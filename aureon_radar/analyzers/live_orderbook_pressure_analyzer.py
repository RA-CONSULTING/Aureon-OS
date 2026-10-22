"""Live orderbook pressure analyzer — REAL market data (Binance public REST).

Analyzer-layer real-signal module for the hub's SignalFusionEngine. Follows
the binding conventions of scanners/live_market_momentum_scanner.py:

  * module-level ``analyze(symbol, price)`` — the hub probes this name.
  * returns dict {"direction": "LONG"|"SHORT"|"NEUTRAL", "confidence": 0..1}
    or None. Low conviction returns None and the source is omitted from
    fusion — never force a direction to fake participation.
  * hub symbols mapped via SYMBOL_MAP; anything unmapped returns None.
  * REAL data only. Any network failure / non-200 / malformed payload ->
    None. Never synthesise book or tape numbers.
  * ~45s per-symbol cache; hard per-call timeout <=5s (depth 3.0s +
    trades 2.0s worst case).

Score mapping (documented):
  depth_imb = (bid_usd - ask_usd) / (bid_usd + ask_usd)   over top-100
              levels, USD-weighted (price * qty summed per side)
  tape_bias = (taker_buy_qty - taker_sell_qty) / (total qty)  over the
              last 100 trades; on Binance ``isBuyerMaker=False`` == taker
              buy (aggressor lifted the ask).
  score     = 0.6 * depth_imb + 0.4 * tape_bias   (tape term dropped to
              0.0 if the trades fetch fails; depth term is mandatory)
  result    = direction LONG if score > 0 else SHORT,
              confidence = |score| — but None if |score| < 0.35.
A flat book/tape therefore honestly returns None: that is the doctrine
working, not a failure.
"""

from __future__ import annotations

import time
from typing import Optional

import requests

# ── symbol mapping (hub symbol -> Binance public symbol) ────────────────────
SYMBOL_MAP = {
    "BTCUSD": "BTCUSDT", "BTCUSDT": "BTCUSDT", "BTC": "BTCUSDT", "XBTUSD": "BTCUSDT",
    "ETHUSD": "ETHUSDT", "ETHUSDT": "ETHUSDT", "ETH": "ETHUSDT",
}

_BASE = "https://api.binance.com/api/v3"
_DEPTH_TIMEOUT = 3.0
_TRADES_TIMEOUT = 2.0
_CACHE_TTL = 45.0
_cache: dict = {}


def _fetch(symbol: str) -> Optional[dict]:
    now = time.time()
    hit = _cache.get(symbol)
    if hit and now - hit[0] < _CACHE_TTL:
        return hit[1]
    try:
        r = requests.get(f"{_BASE}/depth", params={"symbol": symbol, "limit": 100},
                         timeout=_DEPTH_TIMEOUT)
        if r.status_code != 200:
            return None
        d = r.json()
        bids, asks = d.get("bids"), d.get("asks")
        if not isinstance(bids, list) or not isinstance(asks, list) or not bids or not asks:
            return None

        # tape: best-effort, same call window; failure -> bias 0.0
        tape_bias = 0.0
        try:
            t = requests.get(f"{_BASE}/trades", params={"symbol": symbol, "limit": 100},
                             timeout=_TRADES_TIMEOUT)
            if t.status_code == 200:
                trades = t.json()
                if isinstance(trades, list) and trades:
                    buy = sum(float(x["qty"]) for x in trades
                              if x.get("isBuyerMaker") is False)
                    sell = sum(float(x["qty"]) for x in trades
                               if x.get("isBuyerMaker") is True)
                    tot = buy + sell
                    if tot > 0:
                        tape_bias = (buy - sell) / tot
        except Exception:
            tape_bias = 0.0

        data = {"bids": bids, "asks": asks, "tape_bias": tape_bias}
        _cache[symbol] = (now, data)
        return data
    except Exception:
        return None


def analyze(symbol: str, price: float = 0.0):
    """Hub probe entry — returns dict(direction, confidence) or None."""
    bsym = SYMBOL_MAP.get(str(symbol).upper())
    if bsym is None:
        return None
    d = _fetch(bsym)
    if not d:
        return None

    bid_usd = sum(float(p) * float(q) for p, q in d["bids"])
    ask_usd = sum(float(p) * float(q) for p, q in d["asks"])
    tot_usd = bid_usd + ask_usd
    if tot_usd <= 0:
        return None
    depth_imb = (bid_usd - ask_usd) / tot_usd

    score = 0.6 * depth_imb + 0.4 * d["tape_bias"]
    score = max(-1.0, min(1.0, score))
    conf = abs(score)
    if conf < 0.35:
        return None  # flat tape/book — omit, don't dilute fusion
    return {
        "direction": "LONG" if score > 0 else "SHORT",
        "confidence": round(conf, 4),
        "source": "binance_public_depth100+trades100",
    }


if __name__ == "__main__":
    # live self-test: report real numbers, even when the honest answer is None
    for s in ("BTCUSD", "ETHUSD", "EURUSD"):
        bsym = SYMBOL_MAP.get(s)
        if bsym is None:
            print(f"{s}: unmapped -> None")
            continue
        d = _fetch(bsym)
        if not d:
            print(f"{s}: fetch failed -> None")
            continue
        bid_usd = sum(float(p) * float(q) for p, q in d["bids"])
        ask_usd = sum(float(p) * float(q) for p, q in d["asks"])
        imb = (bid_usd - ask_usd) / (bid_usd + ask_usd)
        print(f"{s}: bid_usd={bid_usd:,.0f} ask_usd={ask_usd:,.0f} "
              f"depth_imb={imb:+.4f} tape_bias={d['tape_bias']:+.4f} "
              f"blended={0.6 * imb + 0.4 * d['tape_bias']:+.4f} -> {analyze(s)}")
