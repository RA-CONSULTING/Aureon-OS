#!/usr/bin/env python3
"""
Lighthouse Metrics Watcher — runs alongside the live Python autopilot.

- Pulls BNBBTC prices at a short interval
- Computes Lighthouse-lite metrics: Q, G_eff, C_lin, C_nonlin, L
- Emits heartbeat + balances + reality (LOT_SIZE, NOTIONAL) constraints
- Does NOT place orders; safe to run in parallel

Files written under ./metrics/
  - lighthouse_autopilot.json
  - heartbeat.json
  - reality_constraints.json

Environment variables used:
  BINANCE_API_KEY, BINANCE_API_SECRET, BINANCE_TESTNET

"""
import os
import time
import hmac
import json
import math
import hashlib
import requests
from collections import deque
from datetime import datetime


API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')
TESTNET = os.getenv('BINANCE_TESTNET', 'false').lower() == 'true'

BASE_URL = "https://testnet.binance.vision/api" if TESTNET else "https://api.binance.com/api"

PAIR = os.getenv('AUREON_PAIR', 'BNBBTC')
METRICS_DIR = os.path.join(os.getcwd(), 'metrics')
os.makedirs(METRICS_DIR, exist_ok=True)

def sign(params: dict) -> dict:
    params = dict(params)
    params['timestamp'] = int(time.time() * 1000)
    query = '&'.join([f"{k}={v}" for k,v in params.items()])
    sig = hmac.new(API_SECRET.encode('utf-8'), query.encode('utf-8'), hashlib.sha256).hexdigest()
    params['signature'] = sig
    return params

def get(path: str, params: dict=None, signed: bool=False):
    headers = {'X-MBX-APIKEY': API_KEY}
    if params is None: params = {}
    if signed:
        params = sign(params)
    r = requests.get(f"{BASE_URL}{path}", headers=headers, params=params, timeout=10)
    r.raise_for_status()
    return r.json()

def fetch_balances():
    try:
        acct = get('/v3/account', signed=True)
        bals = {b['asset']: float(b['free']) + float(b['locked']) for b in acct.get('balances', [])}
        return {
            'BTC': bals.get('BTC', 0.0),
            'BNB': bals.get('BNB', 0.0),
            'ETH': bals.get('ETH', 0.0),
            'LDUSDC': bals.get('LDUSDC', 0.0),
        }
    except Exception:
        return {}

def fetch_exchange_rules(symbol: str):
    data = get('/v3/exchangeInfo', params={'symbol': symbol})
    rules = {
        'symbol': symbol,
        'status': None,
        'lotSize': {'minQty':'0', 'stepSize':'0'},
        'notional': {'minNotional':'0'},
    }
    for s in data.get('symbols', []):
        if s.get('symbol') == symbol:
            rules['status'] = s.get('status')
            for f in s.get('filters', []):
                if f.get('filterType') == 'LOT_SIZE':
                    rules['lotSize'] = {'minQty': f.get('minQty','0'), 'stepSize': f.get('stepSize','0')}
                if f.get('filterType') in ('MIN_NOTIONAL','NOTIONAL'):
                    rules['notional'] = {'minNotional': f.get('minNotional','0')}
            break
    return rules

def ema(series, period):
    if not series:
        return 0.0
    k = 2 / (period + 1)
    e = series[0]
    for x in series[1:]:
        e = x * k + e * (1 - k)
    return e

def compute_metrics(price_hist: list, vol_hist: list, ts_hist: list):
    # C_lin via MACD-like EMA spread
    if len(price_hist) < 26:
        C_lin = 0.0
    else:
        ef = ema(price_hist[-26:], 12)
        es = ema(price_hist[-26:], 26)
        macd = ef - es
        C_lin = min(1.0, abs(macd) / (es * 0.05)) if es != 0 else 0.0

    # Volatility inverse for C_nonlin
    if len(price_hist) < 20:
        C_nonlin = 0.0
    else:
        recent = price_hist[-20:]
        m = sum(recent)/len(recent)
        var = sum((p - m)**2 for p in recent)/len(recent)
        vol = math.sqrt(var)/m if m else 0
        C_nonlin = 1.0/(1.0 + vol)

    # |Q| — anomaly pointer: volume spike + price accel
    if len(vol_hist) >= 10:
        mv = sum(vol_hist[-10:])/10
        vol_spike = min(1.0, (vol_hist[-1]/(mv+1)) if mv else 0.0)
    else:
        vol_spike = 0.0

    if len(price_hist) >= 5:
        rp = price_hist[-5:]
        diffs = [rp[i]-rp[i-1] for i in range(1,len(rp))]
        accels = [abs(diffs[i]-diffs[i-1]) for i in range(1,len(diffs))]
        mean_acc = sum(accels)/len(accels) if accels else 0.0
        price = rp[-1]
        accel_n = min(1.0, mean_acc/(price*0.001)) if price else 0.0
    else:
        accel_n = 0.0
    Q = min(1.0, 0.6*vol_spike + 0.4*accel_n)

    # G_eff — simple curvature×contrast proxy
    if len(price_hist) >= 5:
        rp = price_hist[-5:]
        dx1 = rp[-2] - rp[-3]
        dx2 = rp[-1] - rp[-2]
        kappa = abs(dx2 - dx1)/(rp[-2]+1)
        contrast = min(1.0, abs(dx2)/(rp[-2]*0.01)) if rp[-2] else 0.0
        G_eff = min(1.0, kappa * contrast)
    else:
        G_eff = 0.0

    # L — geometric mean with weights (C_lin, C_nonlin, G_eff, Q)
    metrics = [C_lin, C_nonlin, G_eff, Q]
    weights = [1.0, 1.2, 1.2, 0.8]
    if any(m <= 0 for m in metrics):
        L = 0.0
    else:
        prod = 1.0
        for m,w in zip(metrics, weights):
            prod *= m**w
        L = prod ** (1.0/sum(weights))

    return {
        'Q': round(Q,4),
        'G_eff': round(G_eff,4),
        'C_lin': round(C_lin,4),
        'C_nonlin': round(C_nonlin,4),
        'L': round(L,4),
    }

def main():
    if not API_KEY or not API_SECRET:
        print("❌ Missing API credentials for metrics watcher")
        return

    # reality constraints snapshot
    try:
        rules = fetch_exchange_rules(PAIR)
        with open(os.path.join(METRICS_DIR, 'reality_constraints.json'), 'w') as f:
            json.dump({
                'symbol': PAIR,
                'rules': rules,
                'updatedAt': datetime.utcnow().isoformat()+'Z'
            }, f, indent=2)
    except Exception as e:
        pass

    price_hist = deque(maxlen=300)
    vol_hist = deque(maxlen=300)
    ts_hist = deque(maxlen=300)

    while True:
        try:
            # price & tiny pseudo-volume proxy via 24h ticker
            tkr = get('/v3/ticker/24hr', params={'symbol': PAIR})
            price = float(tkr.get('lastPrice', '0'))
            volume = float(tkr.get('volume', '0'))
            price_hist.append(price)
            vol_hist.append(volume)
            ts_hist.append(time.time())

            balances = fetch_balances()
            metrics = compute_metrics(list(price_hist), list(vol_hist), list(ts_hist))

            payload = {
                'symbol': PAIR,
                'price': price,
                'balances': balances,
                'metrics': metrics,
                'updatedAt': datetime.utcnow().isoformat()+'Z'
            }
            with open(os.path.join(METRICS_DIR, 'lighthouse_autopilot.json'), 'w') as f:
                json.dump(payload, f, indent=2)

            # heartbeat
            with open(os.path.join(METRICS_DIR, 'heartbeat.json'), 'w') as f:
                json.dump({
                    'service': 'python_autopilot_metrics',
                    'ok': True,
                    'symbol': PAIR,
                    'updatedAt': datetime.utcnow().isoformat()+'Z'
                }, f)

        except Exception:
            # write a minimal heartbeat on error
            with open(os.path.join(METRICS_DIR, 'heartbeat.json'), 'w') as f:
                json.dump({
                    'service': 'python_autopilot_metrics',
                    'ok': False,
                    'symbol': PAIR,
                    'updatedAt': datetime.utcnow().isoformat()+'Z'
                }, f)

        time.sleep(5)


if __name__ == '__main__':
    main()
