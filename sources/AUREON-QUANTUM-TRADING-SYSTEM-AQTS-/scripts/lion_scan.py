#!/usr/bin/env python3
"""
Lion Scan — pride-wide market scanner.

- Confirms which symbols are TRADING and permitted for account
- Prioritizes pairs based on current balances (bees focus on honey)
- Emits metrics/lion_scan.json with suggestions

Safe to run in parallel with autopilot.
"""
import os
import time
import json
import hmac
import hashlib
import requests
from datetime import datetime

API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')
TESTNET = os.getenv('BINANCE_TESTNET', 'false').lower() == 'true'
BASE_URL = "https://testnet.binance.vision/api" if TESTNET else "https://api.binance.com/api"

DEFAULT_SYMBOLS = ['BNBBTC','ETHBTC','BTCUSDT','BNBUSDT','ETHUSDT']
LION_SYMBOLS = os.getenv('LION_SYMBOLS')
SYMBOLS = [s.strip().upper() for s in LION_SYMBOLS.split(',')] if LION_SYMBOLS else DEFAULT_SYMBOLS

def sign(params: dict) -> dict:
    params = dict(params)
    params['timestamp'] = int(time.time() * 1000)
    q = '&'.join([f"{k}={v}" for k,v in params.items()])
    sig = hmac.new(API_SECRET.encode('utf-8'), q.encode('utf-8'), hashlib.sha256).hexdigest()
    params['signature'] = sig
    return params

def get(path, params=None, signed=False):
    headers = {'X-MBX-APIKEY': API_KEY}
    if params is None: params = {}
    if signed: params = sign(params)
    r = requests.get(f"{BASE_URL}{path}", headers=headers, params=params, timeout=10)
    r.raise_for_status()
    return r.json()

def test_permitted(symbol: str) -> bool:
    headers = {'X-MBX-APIKEY': API_KEY}
    params = sign({'symbol': symbol, 'side':'BUY', 'type':'MARKET', 'quoteOrderQty':'5.01'})
    r = requests.post(f"{BASE_URL}/v3/order/test", headers=headers, params=params)
    if r.status_code == 200:
        return True
    msg = ''
    try:
        msg = r.json().get('msg','')
    except Exception:
        pass
    return 'not permitted' not in msg.lower()

def main():
    if not API_KEY or not API_SECRET:
        print('❌ Missing API credentials for Lion scan')
        return
    os.makedirs('metrics', exist_ok=True)

    while True:
        try:
            acct = get('/v3/account', signed=True)
            balances = {b['asset']: float(b['free'])+float(b['locked']) for b in acct.get('balances', [])}
            suggestions = []
            for sym in SYMBOLS:
                ex = get('/v3/exchangeInfo', params={'symbol': sym})
                status = 'UNKNOWN'
                for s in ex.get('symbols', []):
                    if s.get('symbol') == sym:
                        status = s.get('status','UNKNOWN')
                        break
                permitted = test_permitted(sym)
                weight = 0
                # Simple priority: if have base or quote assets
                base, quote = sym[:-3], sym[-3:]
                # Handle common 4-letter quotes like USDT, BUSD
                if sym.endswith('USDT'):
                    base = sym[:-4]
                    quote = 'USDT'
                if balances.get(base,0) > 0: weight += 2
                if balances.get(quote,0) > 0: weight += 1
                suggestions.append({'symbol': sym, 'status': status, 'permitted': permitted, 'weight': weight})
            suggestions.sort(key=lambda x: (x['permitted'], x['status']=='TRADING', x['weight']), reverse=True)
            out = {
                'updatedAt': datetime.utcnow().isoformat()+'Z',
                'balances': {k:v for k,v in balances.items() if v>0},
                'suggestions': suggestions[:10]
            }
            with open(os.path.join('metrics','lion_scan.json'), 'w') as f:
                json.dump(out, f, indent=2)
        except Exception:
            pass
        time.sleep(10)

if __name__ == '__main__':
    main()
