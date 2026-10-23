import os
import time
import hmac
import hashlib
import requests


TESTNET = os.getenv('BINANCE_TESTNET', 'false').lower() == 'true'
BASE_URL = "https://testnet.binance.vision/api" if TESTNET else "https://api.binance.com/api"
API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')
DRY_RUN = os.getenv('EPICENTER_LIVE', 'NO') != 'YES'


def _sign(params: dict) -> dict:
    p = dict(params)
    p['timestamp'] = int(time.time() * 1000)
    qs = '&'.join([f"{k}={v}" for k,v in p.items()])
    sig = hmac.new(API_SECRET.encode('utf-8'), qs.encode('utf-8'), hashlib.sha256).hexdigest()
    p['signature'] = sig
    return p


def place_market(symbol: str, side: str, quantity: float):
    if DRY_RUN:
        return {'dryRun': True, 'symbol': symbol, 'side': side, 'quantity': quantity, 'orderId': 0}
    headers = {'X-MBX-APIKEY': API_KEY}
    params = _sign({'symbol': symbol, 'side': side, 'type': 'MARKET', 'quantity': quantity})
    r = requests.post(f"{BASE_URL}/v3/order", headers=headers, params=params, timeout=10)
    r.raise_for_status()
    return r.json()
