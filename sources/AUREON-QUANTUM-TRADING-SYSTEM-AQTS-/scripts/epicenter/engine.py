#!/usr/bin/env python3
"""
Epicenter orchestrator — multi-symbol, multi-strategy spot trading (dry-run by default).

Safety:
- Requires EPICENTER_LIVE=YES to place real orders; otherwise dry-run
- Requires CONFIRM_EPICENTER=YES to start
- Limits symbol count via EPICENTER_SYMBOLS or discovery (top N by volume)
"""
import os
import time
import json
import queue
import random
import threading
from datetime import datetime, timezone

import requests
try:
    import websocket
except ImportError:
    raise SystemExit("Missing dependency 'websocket-client'. Install: pip install websocket-client")

from .universe import fetch_spot_universe
from .strategy_api import MeanReversion, Momentum
from .risk import enforce_rules
from .router import place_market


TESTNET = os.getenv('BINANCE_TESTNET', 'false').lower() == 'true'
HTTP_BASE = "https://testnet.binance.vision/api" if TESTNET else "https://api.binance.com/api"
WS_BASE = "wss://stream.testnet.binance.vision/stream" if TESTNET else "wss://stream.binance.com:9443/stream"

DRY_RUN = os.getenv('EPICENTER_LIVE', 'NO') != 'YES'


def iso():
    return datetime.now(timezone.utc).isoformat()


def get_exchange_rules(symbol):
    try:
        r = requests.get(f"{HTTP_BASE}/v3/exchangeInfo", params={'symbol': symbol}, timeout=10)
        r.raise_for_status()
        info = r.json()
        for s in info.get('symbols', []):
            if s.get('symbol') == symbol:
                base = s.get('baseAsset'); quote = s.get('quoteAsset')
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


def combined_stream(symbols):
    streams = '/'.join([f"{s.lower()}@ticker" for s in symbols])
    return f"{WS_BASE}?streams={streams}"


def load_lighthouse_gate():
    try:
        with open(os.path.join('metrics','lighthouse_autopilot.json'), 'r') as f:
            m = json.load(f).get('metrics', {})
        L_MIN = float(os.getenv('LIGHTHOUSE_L_MIN', '0.0'))
        G_MAX = float(os.getenv('LIGHTHOUSE_G_MAX', '1.0'))
        Q_MAX = float(os.getenv('LIGHTHOUSE_Q_MAX', '1.0'))
        L = float(m.get('L', 0.0)); G = float(m.get('G_eff', 0.0)); Q = float(m.get('Q', 0.0))
        return (L >= L_MIN) and (G <= G_MAX) and (Q <= Q_MAX)
    except Exception:
        return os.getenv('LIGHTHOUSE_L_MIN', '0.0') == '0.0'


def main():
    if os.getenv('CONFIRM_EPICENTER') != 'YES':
        print("❌ Set CONFIRM_EPICENTER=YES to start Epicenter")
        return

    # Symbols
    env_syms = os.getenv('EPICENTER_SYMBOLS')
    if env_syms:
        symbols = [s.strip().upper() for s in env_syms.split(',') if s.strip()]
    else:
        print("🔎 Discovering universe (top 20 by 24h volume, quotes USDT,BTC)")
        symbols = fetch_spot_universe({'USDT','BTC'}, min_volume_usdt=2_000_000, limit=20)
    if not symbols:
        print("❌ No symbols to trade")
        return

    print(f"🚀 Epicenter starting on {len(symbols)} symbols | mode={'DRY' if DRY_RUN else 'LIVE'}")

    # Strategies per symbol (flavors)
    strats = {s: [Momentum(fast=5, slow=20), MeanReversion(window=30, z=1.2)] for s in symbols}
    rules = {s: get_exchange_rules(s) for s in symbols}

    # Shared prices map
    prices = {s: 0.0 for s in symbols}

    # WebSocket
    url = combined_stream(symbols)
    qmsg = queue.Queue()

    def on_msg(ws, message):
        try:
            data = json.loads(message)
            payload = data.get('data', {})
            s = payload.get('s'); p = payload.get('c') or payload.get('p')
            if s and p:
                px = float(p)
                prices[s] = px
                for strat in strats.get(s, []):
                    strat.on_price(px)
            qmsg.put(1)
        except Exception:
            pass

    def on_err(ws, err):
        print(f"WS error: {err}")

    def on_close(ws, code, msg):
        print("WS closed", code, msg)

    ws = websocket.WebSocketApp(url, on_message=on_msg, on_error=on_err, on_close=on_close)
    t = threading.Thread(target=ws.run_forever, kwargs={'ping_interval':20,'ping_timeout':10}, daemon=True)
    t.start()

    # Balances (simplified: query once and update roughly via trades)
    bal = {'BTC': 0.001, 'USDT': 100.0}  # seed small balances; production would pull /v3/account

    # Per-symbol next trade time
    next_t = {s: 0.0 for s in symbols}
    cooldown = float(os.getenv('EPICENTER_COOLDOWN_SEC', '20'))
    pos_pct = float(os.getenv('EPICENTER_POSITION_PCT', '0.2'))

    start = time.time()
    trades = 0
    TARGET_PER_SYMBOL = int(os.getenv('EPICENTER_TRADES_PER_SYMBOL', '10'))
    done = {s: 0 for s in symbols}

    print("📡 Waiting for ticks and Lighthouse gate...")
    try:
        while True:
            try:
                qmsg.get(timeout=0.5)
            except queue.Empty:
                pass
            now = time.time()

            # Gate by Lighthouse
            if not load_lighthouse_gate():
                continue

            all_done = True
            for s in symbols:
                if done[s] >= TARGET_PER_SYMBOL:
                    continue
                all_done = False
                if now < next_t[s]:
                    continue
                px = prices.get(s, 0.0)
                if px <= 0:
                    continue
                # Blend strategy votes
                votes = [st.signal() for st in strats[s]]
                side = 'HOLD'
                if votes.count('BUY') > votes.count('SELL') and votes.count('BUY') > 0:
                    side = 'BUY'
                elif votes.count('SELL') > votes.count('BUY') and votes.count('SELL') > 0:
                    side = 'SELL'
                if side == 'HOLD':
                    next_t[s] = now + 2
                    continue

                rule = rules[s]
                base = rule['base']; quote = rule['quote']
                if not base or not quote:
                    next_t[s] = now + 5
                    continue

                spend_asset = quote if side=='BUY' else base
                avail = bal.get(spend_asset, 0.0)
                if avail <= 0:
                    next_t[s] = now + 5
                    continue
                spend_amt = avail * pos_pct
                qty = spend_amt/px if side=='BUY' else spend_amt
                qty = enforce_rules(qty, px, rule['minQty'], rule['stepSize'], rule['minNotional'])
                if not qty:
                    next_t[s] = now + 5
                    continue

                # Place (or dry-run) market order
                try:
                    resp = place_market(s, side, qty)
                    trades += 1
                    done[s] += 1
                    # Update balances roughly
                    if side=='BUY':
                        cost = qty*px
                        bal[quote] = bal.get(quote,0)-cost
                        bal[base] = bal.get(base,0)+qty
                    else:
                        bal[base] = bal.get(base,0)-qty
                        bal[quote] = bal.get(quote,0)+qty*px
                    print(f"{iso()} [{s}] {side} qty={qty:.8f} px={px:.8f} -> orderId={resp.get('orderId',0)}{' DRY' if DRY_RUN else ''}")
                except Exception as e:
                    print(f"Order error {s}: {e}")

                next_t[s] = now + cooldown

            if all_done:
                break
    finally:
        try:
            ws.close()
        except Exception:
            pass

    print(f"🏁 Epicenter complete. trades={trades}, elapsed={time.time()-start:.1f}s")


if __name__ == '__main__':
    main()
