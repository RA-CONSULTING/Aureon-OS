#!/usr/bin/env python3
"""
[SELL]⚡ GAIA AGGRESSIVE RECLAIMER ⚡[SELL]
NO GATES. NO WAITING. JUST TAKE.

Based on the WORKING rotations from this chat:
- Buy SOL → Wait → Sell SOL → Buy BTC → Wait → Sell BTC → Repeat
- Any profit = TAKE IT
- Deploy ALL cash immediately
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys, os
os.environ['PYTHONUNBUFFERED'] = '1'

import time
import math
import csv
import asyncio
import requests
import statistics
import json
import random
from collections import deque
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import threading

try:
    import websockets
except Exception:
    websockets = None

try:
    from aureon.strategies.probability_ultimate_intelligence import ultimate_predict
except Exception:
    ultimate_predict = None

try:
    from aureon.strategies.probability_intelligence_matrix import calculate_intelligent_probability
except Exception:
    calculate_intelligent_probability = None

try:
    from aureon.strategies.probability_loader import ProbabilityLoader
except Exception:
    ProbabilityLoader = None

try:
    from aureon.strategies.hnc_probability_matrix import HNCProbabilityIntegration
except Exception:
    HNCProbabilityIntegration = None

try:
    from aureon.trading.aureon_barter_navigator import BarterNavigator, get_barter_score
except Exception:
    BarterNavigator = None
    get_barter_score = None

try:
    from aureon.conversion.aureon_conversion_ladder import ConversionLadder
except Exception:
    ConversionLadder = None

try:
    from aureon.bridges.aureon_bridge import AureonBridge, Opportunity, CapitalState, Position as BridgePosition
except Exception:
    AureonBridge = None
    Opportunity = None
    CapitalState = None
    BridgePosition = None

try:
    from aureon.core.aureon_thought_bus import get_thought_bus, Thought
except Exception:
    get_thought_bus = None
    Thought = None

try:
    from aureon.core.aureon_mycelium import get_mycelium
except Exception:
    get_mycelium = None

try:
    from aureon.intelligence.aureon_market_pulse import MarketPulse
except Exception:
    MarketPulse = None

try:
    from aureon.trading.aureon_commandos import PrideScanner, LionHunt
except Exception:
    PrideScanner = None
    LionHunt = None

try:
    from aureon.trading.aureon_auris_trader import AurisEngine, MarketSnapshot
except Exception:
    AurisEngine = None
    MarketSnapshot = None

try:
    from aureon.bridges.aureon_probability_nexus import MeanReversionDetector, PhaseAligner, ProbabilityMatrix, HarmonicAnalyzer
except Exception:
    MeanReversionDetector = None
    PhaseAligner = None
    ProbabilityMatrix = None
    HarmonicAnalyzer = None

try:
    from aureon.intelligence.aureon_advanced_intelligence import calculate_golden_ratio_alignment
except Exception:
    calculate_golden_ratio_alignment = None

try:
    from aureon.trading.unified_exchange_client import MultiExchangeClient
except Exception:
    MultiExchangeClient = None

try:
    from aureon.core.aureon_lattice import LatticeEngine
except Exception:
    LatticeEngine = None

try:
    from aureon.utils.aureon_luck_field_mapper import get_luck_mapper
except Exception:
    get_luck_mapper = None

try:
    from aureon.core.mycelium_whale_sonar import ensure_sonar
except Exception:
    ensure_sonar = None

sys.path.append(os.getcwd())

# Sacred Constants
PHI = (1 + math.sqrt(5)) / 2
SCHUMANN = 7.83

class MarketRadar:
    def __init__(self, alpaca):
        self.alpaca = alpaca
        self.cache = {}
        self.cache_ttl = 20.0
        self.validation_cache = {}
        self.validation_cache_ttl = float(os.getenv("HIVE_VALIDATION_CACHE_TTL", "3"))
        self.kraken_pairs = None
        self.kraken_pairs_ts = 0.0
        self.kraken_pair_ttl = 3600.0
        self.use_binance = os.getenv("HIVE_USE_BINANCE", "true").lower() == "true"
        self.use_coinbase = os.getenv("HIVE_USE_COINBASE", "true").lower() == "true"
        self.use_kraken = os.getenv("HIVE_USE_KRAKEN", "false").lower() == "true"
        self.use_coinbase_tickers = os.getenv("HIVE_USE_COINBASE_TICKERS", "true").lower() == "true"
        self.use_binance_ws = os.getenv("HIVE_USE_BINANCE_WS", "true").lower() == "true"
        self.use_coinbase_ws = os.getenv("HIVE_USE_COINBASE_WS", "true").lower() == "true"
        self.use_kraken_ws = os.getenv("HIVE_USE_KRAKEN_WS", "true").lower() == "true"
        # Hardcoded Queen defaults: disable cross-exchange validation
        self.use_binance = False
        self.use_coinbase = False
        self.use_kraken = False
        self.use_coinbase_tickers = False
        self.use_binance_ws = False
        self.use_coinbase_ws = False
        self.use_kraken_ws = False
        self.binance_ws_timeout = float(os.getenv("HIVE_BINANCE_WS_STALE", "5"))
        self.binance_ws_data = {}
        self.binance_ws_last = 0.0
        self._binance_ws_thread = None
        self.coinbase_ws_timeout = float(os.getenv("HIVE_COINBASE_WS_STALE", "5"))
        self.coinbase_ws_batch = int(os.getenv("HIVE_COINBASE_WS_BATCH", "50"))
        self.coinbase_ws_rotate = float(os.getenv("HIVE_COINBASE_WS_ROTATE", "20"))
        self.coinbase_ws_data = {}
        self.coinbase_ws_last = 0.0
        self.coinbase_ws_cursor = 0
        self._coinbase_ws_thread = None
        self.kraken_ws_timeout = float(os.getenv("HIVE_KRAKEN_WS_STALE", "5"))
        self.kraken_ws_batch = int(os.getenv("HIVE_KRAKEN_WS_BATCH", "30"))
        self.kraken_ws_rotate = float(os.getenv("HIVE_KRAKEN_WS_ROTATE", "20"))
        self.kraken_ws_data = {}
        self.kraken_ws_last = 0.0
        self.kraken_ws_cursor = 0
        self._kraken_ws_thread = None
        self.coinbase_cursor = 0
        self.coinbase_batch = int(os.getenv("HIVE_COINBASE_BATCH", "9"))
        self.coinbase_interval = float(os.getenv("HIVE_COINBASE_INTERVAL", "3"))
        self.coinbase_last_fetch = 0.0
        self.coinbase_focus_limit = int(os.getenv("HIVE_COINBASE_FOCUS", str(self.coinbase_batch)))
        self.scan_batch_total = int(os.getenv("HIVE_SCAN_BATCH_SIZE", "10"))
        self.alpaca_cursor = 0
        self.alpaca_validation_limit = int(os.getenv("HIVE_ALPACA_VALIDATION", "1"))
        self.last_focus_bases = []
        self.last_validation_base = None
        self.last_consensus = {}
        self.coinbase_products = {}
        self.coinbase_products_ts = 0.0
        self.coinbase_products_ttl = 3600.0
        # Hardcoded Queen defaults (no env overrides)
        self.coinbase_interval = 3.0
        self.scan_batch_total = 10
        self.price_history = {}
        self.price_history_window = float(os.getenv("HIVE_PRICE_HISTORY_WINDOW_MIN", "15")) * 60.0
        self.price_history_limit = int(os.getenv("HIVE_PRICE_HISTORY_LIMIT", "600"))
        self.price_history_lock = threading.Lock()

        if self.use_binance_ws and websockets:
            self._start_binance_stream()
        if self.use_coinbase_ws and websockets:
            self._start_coinbase_stream()
        if self.use_kraken_ws and websockets:
            self._start_kraken_stream()

    def _cache_get(self, key):
        entry = self.cache.get(key)
        if not entry:
            return None
        ts, val = entry
        if time.time() - ts > self.cache_ttl:
            return None
        return val

    def _cache_set(self, key, val):
        self.cache[key] = (time.time(), val)

    def _record_price(self, base, price, source):
        if price <= 0:
            return
        now = time.time()
        with self.price_history_lock:
            history = self.price_history.get(base)
            if history is None:
                history = deque(maxlen=self.price_history_limit)
                self.price_history[base] = history
            history.append({"ts": now, "price": float(price), "source": source})

    def get_price_history(self, base, limit=120, window_sec=None):
        now = time.time()
        with self.price_history_lock:
            history = list(self.price_history.get(base, []))
        if not history:
            return []
        if window_sec is None:
            window_sec = self.price_history_window
        history = [h for h in history if now - h["ts"] <= window_sec]
        if limit and len(history) > limit:
            history = history[-limit:]
        return history

    def get_live_window_metrics(self, base, lookback_sec=420.0, projection_sec=420.0):
        now = time.time()
        with self.price_history_lock:
            history = list(self.price_history.get(base, []))
        if not history:
            return None
        preferred_sources = {
            "binance", "kraken", "binance_ws", "kraken_ws", "binance_rest", "kraken_rest"
        }
        preferred = [h for h in history if h.get("source") in preferred_sources]
        history = preferred if preferred else history
        history = [h for h in history if now - h["ts"] <= self.price_history_window]
        if not history:
            return None
        history.sort(key=lambda h: h["ts"])
        newest = history[-1]
        oldest = None
        cutoff = now - lookback_sec
        for entry in history:
            if entry["ts"] >= cutoff:
                oldest = entry
                break
        if oldest is None:
            oldest = history[0]
        dt = max(1e-6, newest["ts"] - oldest["ts"])
        last_price = newest["price"]
        past_price = oldest["price"]
        if past_price <= 0 or last_price <= 0:
            return None
        delta_pct = (last_price - past_price) / past_price * 100.0
        slope = (last_price - past_price) / dt
        projected = last_price + slope * projection_sec
        projection_pct = (projected - last_price) / last_price * 100.0
        return {
            "delta_pct": delta_pct,
            "projection_pct": projection_pct,
            "samples": len(history),
            "age_sec": now - newest["ts"],
        }

    def _start_binance_stream(self):
        if self._binance_ws_thread:
            return
        self._binance_ws_thread = threading.Thread(target=self._binance_ws_loop, daemon=True)
        self._binance_ws_thread.start()

    def _binance_ws_loop(self):
        if not websockets:
            return

        async def _run():
            url = "wss://stream.binance.com:9443/ws/!ticker@arr"
            while True:
                try:
                    async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
                        async for msg in ws:
                            try:
                                payload = json.loads(msg)
                            except Exception:
                                continue
                            if not isinstance(payload, list):
                                continue
                            data = {}
                            for item in payload:
                                sym = item.get("s", "")
                                if not sym.endswith("USDT") and not sym.endswith("USDC"):
                                    continue
                                base = sym.replace("USDT", "").replace("USDC", "")
                                try:
                                    change = float(item.get("P", 0) or 0)
                                except Exception:
                                    change = 0.0
                                try:
                                    price = float(item.get("c", 0) or 0)
                                except Exception:
                                    price = 0.0
                                try:
                                    volume = float(item.get("q", 0) or 0)
                                except Exception:
                                    volume = 0.0
                                data[base] = {
                                    "change": change,
                                    "price": price,
                                    "volume": volume,
                                }
                                if price > 0:
                                    self._record_price(base, price, "binance")
                            if data:
                                self.binance_ws_data = data
                                self.binance_ws_last = time.time()
                except Exception:
                    await asyncio.sleep(1)

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_run())
        except Exception:
            return

    def _start_coinbase_stream(self):
        if self._coinbase_ws_thread:
            return
        self._coinbase_ws_thread = threading.Thread(target=self._coinbase_ws_loop, daemon=True)
        self._coinbase_ws_thread.start()

    def _coinbase_ws_loop(self):
        if not websockets:
            return

        async def _run():
            url = "wss://ws-feed.exchange.coinbase.com"
            while True:
                products = list(self.get_coinbase_products().keys())
                if not products:
                    await asyncio.sleep(2)
                    continue
                batch = self._rotate_bases(products, self.coinbase_ws_batch, "coinbase_ws_cursor")
                product_ids = [f"{b}-USD" for b in batch]
                try:
                    async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
                        sub = {
                            "type": "subscribe",
                            "channels": [{"name": "ticker", "product_ids": product_ids}],
                        }
                        await ws.send(json.dumps(sub))
                        start = time.time()
                        while True:
                            if time.time() - start >= self.coinbase_ws_rotate:
                                break
                            try:
                                msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                            except asyncio.TimeoutError:
                                continue
                            try:
                                payload = json.loads(msg)
                            except Exception:
                                continue
                            if payload.get("type") != "ticker":
                                continue
                            product = payload.get("product_id", "")
                            if not product or "-" not in product:
                                continue
                            base = product.split("-", 1)[0]
                            try:
                                price = float(payload.get("price", 0) or 0)
                            except Exception:
                                price = 0.0
                            try:
                                open_price = float(payload.get("open_24h", 0) or 0)
                            except Exception:
                                open_price = 0.0
                            change = ((price - open_price) / open_price * 100) if open_price else 0.0
                            try:
                                volume = float(payload.get("volume_24h", 0) or 0)
                            except Exception:
                                volume = 0.0
                            self.coinbase_ws_data[base] = {
                                "change": change,
                                "price": price,
                                "volume": volume * price if price > 0 else 0.0,
                            }
                            if price > 0:
                                self._record_price(base, price, "coinbase")
                            self.coinbase_ws_last = time.time()
                except Exception:
                    await asyncio.sleep(1)

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_run())
        except Exception:
            return

    def _start_kraken_stream(self):
        if self._kraken_ws_thread:
            return
        self._kraken_ws_thread = threading.Thread(target=self._kraken_ws_loop, daemon=True)
        self._kraken_ws_thread.start()

    def _kraken_ws_loop(self):
        if not websockets:
            return

        async def _run():
            url = "wss://ws.kraken.com/"
            while True:
                pairs_map = self._fetch_kraken_pairs() or {}
                pairs = list(pairs_map.values())
                if not pairs:
                    await asyncio.sleep(2)
                    continue
                batch = self._rotate_bases(pairs, self.kraken_ws_batch, "kraken_ws_cursor")
                reverse = {v: k for k, v in pairs_map.items()}
                try:
                    async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
                        sub = {"event": "subscribe", "pair": batch, "subscription": {"name": "ticker"}}
                        await ws.send(json.dumps(sub))
                        start = time.time()
                        while True:
                            if time.time() - start >= self.kraken_ws_rotate:
                                break
                            try:
                                msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                            except asyncio.TimeoutError:
                                continue
                            try:
                                payload = json.loads(msg)
                            except Exception:
                                continue
                            if not isinstance(payload, list) or len(payload) < 4:
                                continue
                            data = payload[1]
                            pair = payload[3]
                            base = reverse.get(pair)
                            if not base or not isinstance(data, dict):
                                continue
                            try:
                                price = float(data.get("c", [0])[0] or 0)
                            except Exception:
                                price = 0.0
                            try:
                                open_price = float(data.get("o", [0])[0] or 0)
                            except Exception:
                                open_price = 0.0
                            change = ((price - open_price) / open_price * 100) if open_price else 0.0
                            try:
                                volume = float(data.get("v", [0, 0])[1] or 0)
                            except Exception:
                                volume = 0.0
                            self.kraken_ws_data[base] = {
                                "change": change,
                                "price": price,
                                "volume": volume * price if price > 0 else 0.0,
                            }
                            if price > 0:
                                self._record_price(base, price, "kraken")
                            self.kraken_ws_last = time.time()
                except Exception:
                    await asyncio.sleep(1)

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_run())
        except Exception:
            return

    def _rotate_bases(self, bases, limit, cursor_attr):
        if not bases or limit <= 0:
            return []
        if limit >= len(bases):
            setattr(self, cursor_attr, 0)
            return list(bases)
        cursor = getattr(self, cursor_attr, 0) % len(bases)
        end = cursor + limit
        if end <= len(bases):
            subset = bases[cursor:end]
        else:
            subset = bases[cursor:] + bases[:end - len(bases)]
        setattr(self, cursor_attr, end % len(bases))
        return subset

    def get_scan_bases(self, alpaca_bases):
        bases = list(alpaca_bases or [])
        if not bases:
            return [], None

        products = self.get_coinbase_products()
        coinbase_candidates = [b for b in bases if b in products] if products else bases

        cb_limit = max(1, min(self.coinbase_focus_limit, self.scan_batch_total - 1))
        coinbase_focus = self._rotate_bases(coinbase_candidates, cb_limit, "coinbase_cursor")

        validation = None
        if self.alpaca_validation_limit > 0:
            validation_list = self._rotate_bases(bases, self.alpaca_validation_limit, "alpaca_cursor")
            if validation_list:
                validation = validation_list[0]
                if validation in coinbase_focus and len(bases) > len(coinbase_focus):
                    # Advance once more to avoid duplicate slot
                    validation_list = self._rotate_bases(bases, 1, "alpaca_cursor")
                    if validation_list:
                        validation = validation_list[0]

        self.last_focus_bases = list(coinbase_focus)
        self.last_validation_base = validation
        return coinbase_focus, validation

    def _fetch_binance_24h(self):
        if not self.use_binance:
            return {}
        if self.use_binance_ws and self.binance_ws_data:
            age = time.time() - self.binance_ws_last
            if age <= self.binance_ws_timeout:
                return self.binance_ws_data
        cached = self._cache_get("binance_24h")
        if cached is not None:
            return cached

        url = "https://api.binance.com/api/v3/ticker/24hr"
        try:
            resp = requests.get(url, timeout=8)
            data = resp.json() if resp.ok else []
        except Exception:
            data = []

        changes = {}
        for item in data or []:
            sym = item.get('symbol', '')
            if not sym.endswith('USDT') and not sym.endswith('USDC'):
                continue
            base = sym.replace('USDT', '').replace('USDC', '')
            try:
                change = float(item.get('priceChangePercent', 0))
            except Exception:
                change = 0.0
            try:
                price = float(item.get('lastPrice', 0) or 0)
            except Exception:
                price = 0.0
            try:
                volume = float(item.get('quoteVolume', 0) or 0)
            except Exception:
                volume = 0.0
            existing = changes.get(base)
            if not existing or change > existing.get('change', -999):
                changes[base] = {
                    'change': change,
                    'price': price,
                    'volume': volume,
                }

        self._cache_set("binance_24h", changes)
        return changes

    def _coinbase_focus_bases(self, bases):
        focus, _ = self.get_scan_bases(bases)
        return focus

    def _fetch_coinbase_stats(self, bases):
        if not self.use_coinbase:
            return {}
        if self.use_coinbase_ws and self.coinbase_ws_data:
            age = time.time() - self.coinbase_ws_last
            if age <= self.coinbase_ws_timeout:
                ws_subset = {b: self.coinbase_ws_data.get(b) for b in bases if b in self.coinbase_ws_data}
                if ws_subset:
                    return ws_subset
        cached = self._cache_get("coinbase_24h")
        if cached is None:
            cached = {}

        if not bases:
            return cached

        now = time.time()
        if now - self.coinbase_last_fetch < self.coinbase_interval:
            return cached
        self.coinbase_last_fetch = now

        for base in bases:
            product = f"{base}-USD"
            url = f"https://api.exchange.coinbase.com/products/{product}/stats"
            try:
                resp = requests.get(url, timeout=6)
                if not resp.ok:
                    continue
                stats = resp.json()
                open_price = float(stats.get('open', 0) or 0)
                last = float(stats.get('last', 0) or 0)
                if open_price > 0:
                    change = (last - open_price) / open_price * 100
                else:
                    change = 0.0
                try:
                    volume = float(stats.get('volume', 0) or 0)
                except Exception:
                    volume = 0.0
                cached[base] = {
                    'change': change,
                    'price': last,
                    'volume': volume,
                }
            except Exception:
                continue

        self._cache_set("coinbase_24h", cached)
        return cached

    def get_coinbase_products(self):
        if not self.use_coinbase:
            return {}
        if self.coinbase_products and (time.time() - self.coinbase_products_ts) < self.coinbase_products_ttl:
            return self.coinbase_products

        url = "https://api.exchange.coinbase.com/products"
        products = {}
        try:
            resp = requests.get(url, timeout=10)
            data = resp.json() if resp.ok else []
            for item in data or []:
                base = item.get('base_currency')
                quote = item.get('quote_currency')
                if not base or not quote or quote != 'USD':
                    continue
                products[base] = {
                    'id': item.get('id'),
                    'status': item.get('status'),
                    'base_increment': item.get('base_increment'),
                    'quote_increment': item.get('quote_increment'),
                }
        except Exception:
            products = {}

        self.coinbase_products = products
        self.coinbase_products_ts = time.time()
        return products

    def _fetch_kraken_pairs(self):
        if not (self.use_kraken or self.use_kraken_ws):
            return {}
        if self.kraken_pairs and (time.time() - self.kraken_pairs_ts) < self.kraken_pair_ttl:
            return self.kraken_pairs

        url = "https://api.kraken.com/0/public/AssetPairs"
        pairs = {}
        try:
            resp = requests.get(url, timeout=10)
            data = resp.json() if resp.ok else {}
            for key, info in (data.get('result') or {}).items():
                quote = info.get('quote') or ''
                base = info.get('base') or ''
                if quote not in ('ZUSD', 'USD'):
                    continue
                if base.startswith('X') or base.startswith('Z'):
                    base = base[1:]
                pairs[base] = key
        except Exception:
            pairs = {}

        self.kraken_pairs = pairs
        self.kraken_pairs_ts = time.time()
        return pairs

    def _fetch_kraken_24h(self, bases):
        if not (self.use_kraken or self.use_kraken_ws):
            return {}
        if self.use_kraken_ws and self.kraken_ws_data:
            age = time.time() - self.kraken_ws_last
            if age <= self.kraken_ws_timeout:
                ws_subset = {b: self.kraken_ws_data.get(b) for b in bases if b in self.kraken_ws_data}
                if ws_subset:
                    return ws_subset
        cached = self._cache_get("kraken_24h")
        if cached is None:
            cached = {}

        pairs = self._fetch_kraken_pairs()
        symbols = [pairs.get(b) for b in bases if pairs.get(b)]
        if not symbols:
            return cached

        chunk_size = 20
        for i in range(0, len(symbols), chunk_size):
            chunk = symbols[i:i + chunk_size]
            url = "https://api.kraken.com/0/public/Ticker"
            try:
                resp = requests.get(url, params={"pair": ",".join(chunk)}, timeout=10)
                data = resp.json() if resp.ok else {}
                result = data.get('result') or {}
                for pair_key, vals in result.items():
                    base = None
                    for b, k in pairs.items():
                        if k == pair_key:
                            base = b
                            break
                    if not base:
                        continue
                    try:
                        open_price = float(vals.get('o', 0) or 0)
                        last = float(vals.get('c', [0])[0] or 0)
                        change = (last - open_price) / open_price * 100 if open_price else 0.0
                    except Exception:
                        change = 0.0
                    cached[base] = change
            except Exception:
                continue

        self._cache_set("kraken_24h", cached)
        return cached

    def get_crypto_consensus(self, bases):
        bases = list(bases or [])
        focus_bases, validation_base = self.get_scan_bases(bases)

        products = self.get_coinbase_products() if self.use_coinbase else {}
        binance = self._fetch_binance_24h()
        coinbase_bases = [b for b in focus_bases if b in products] if products else focus_bases
        coinbase = self._fetch_coinbase_stats(coinbase_bases)
        kraken = self._fetch_kraken_24h(focus_bases)

        consensus = {}
        for base in focus_bases:
            vals = []
            sources = 0
            for src in (binance, coinbase, kraken):
                if base in src:
                    val = src[base]
                    if isinstance(val, dict):
                        val = val.get('change', 0.0)
                    vals.append(val)
                    sources += 1
            if not vals:
                continue
            consensus[base] = {
                'avg': sum(vals) / len(vals),
                'max': max(vals),
                'sources': sources,
            }
        self.last_consensus = consensus
        return consensus, set(focus_bases), validation_base

    def build_full_market_snapshot(self):
        limit = int(os.getenv("HIVE_FULL_MARKET_STORE_LIMIT", "200"))
        binance = self._fetch_binance_24h()
        movers = []
        if isinstance(binance, dict):
            for base, data in binance.items():
                if not isinstance(data, dict):
                    continue
                movers.append({
                    "base": base,
                    "change": float(data.get("change", 0) or 0),
                    "price": float(data.get("price", 0) or 0),
                    "volume": float(data.get("volume", 0) or 0),
                })
        movers_by_change = sorted(movers, key=lambda x: x["change"], reverse=True)[:limit]
        movers_by_volume = sorted(movers, key=lambda x: x["volume"], reverse=True)[:limit]
        coinbase_products = self.get_coinbase_products() if self.use_coinbase else {}
        snapshot = {
            "ts": datetime.now().isoformat(),
            "binance_count": len(movers),
            "coinbase_products_count": len(coinbase_products),
            "top_change": movers_by_change,
            "top_volume": movers_by_volume,
        }
        return snapshot

    def get_free_tickers(self, bases):
        tickers = []
        if not bases:
            return tickers
        binance = self._fetch_binance_24h()
        coinbase = {}
        coinbase_ws = self.coinbase_ws_data if self.use_coinbase_ws else {}
        kraken_ws = self.kraken_ws_data if self.use_kraken_ws else {}
        missing_for_cb = []
        for base in bases:
            data = binance.get(base) if isinstance(binance, dict) else None
            if not isinstance(data, dict) or float(data.get('price', 0) or 0) <= 0:
                if base in coinbase_ws or base in kraken_ws:
                    continue
                missing_for_cb.append(base)
        if self.use_coinbase_tickers and missing_for_cb:
            coinbase = self._fetch_coinbase_stats(missing_for_cb)
        for base in bases:
            binance_data = binance.get(base) if isinstance(binance, dict) else None
            coinbase_ws_data = coinbase_ws.get(base) if isinstance(coinbase_ws, dict) else None
            kraken_ws_data = kraken_ws.get(base) if isinstance(kraken_ws, dict) else None
            coinbase_data = coinbase.get(base) if isinstance(coinbase, dict) else None
            price = 0.0
            change = 0.0
            volume = 0.0
            if isinstance(binance_data, dict):
                price = float(binance_data.get('price', 0) or 0)
                change = float(binance_data.get('change', 0) or 0)
                volume = float(binance_data.get('volume', 0) or 0)
            if price <= 0 and isinstance(coinbase_ws_data, dict):
                price = float(coinbase_ws_data.get('price', 0) or 0)
                change = float(coinbase_ws_data.get('change', 0) or 0)
                volume = float(coinbase_ws_data.get('volume', 0) or 0)
            if price <= 0 and isinstance(kraken_ws_data, dict):
                price = float(kraken_ws_data.get('price', 0) or 0)
                change = float(kraken_ws_data.get('change', 0) or 0)
                volume = float(kraken_ws_data.get('volume', 0) or 0)
            if price <= 0 and isinstance(coinbase_data, dict):
                price = float(coinbase_data.get('price', 0) or 0)
            if change == 0 and isinstance(coinbase_data, dict):
                change = float(coinbase_data.get('change', 0) or 0)
            if volume <= 0 and isinstance(coinbase_data, dict):
                base_volume = float(coinbase_data.get('volume', 0) or 0)
                if price > 0:
                    volume = base_volume * price
            if price <= 0 and change == 0:
                continue
            tickers.append({
                'symbol': f"{base}USD",
                'lastPrice': str(price),
                'priceChangePercent': str(change),
                'quoteVolume': str(volume),
            })
        return tickers

    def _fetch_binance_price(self, base):
        for quote in ('USDT', 'USDC'):
            symbol = f"{base}{quote}"
            url = "https://api.binance.com/api/v3/ticker/price"
            try:
                resp = requests.get(url, params={"symbol": symbol}, timeout=6)
                data = resp.json() if resp.ok else {}
                price = float(data.get('price', 0) or 0)
                if price > 0:
                    return price
            except Exception:
                continue
        return 0.0

    def _fetch_coinbase_price(self, base):
        url = f"https://api.exchange.coinbase.com/products/{base}-USD/ticker"
        try:
            resp = requests.get(url, timeout=6)
            data = resp.json() if resp.ok else {}
            return float(data.get('price', 0) or 0)
        except Exception:
            return 0.0

    def _fetch_kraken_price(self, base):
        pairs = self._fetch_kraken_pairs()
        pair = pairs.get(base)
        if not pair:
            return 0.0
        url = "https://api.kraken.com/0/public/Ticker"
        try:
            resp = requests.get(url, params={"pair": pair}, timeout=8)
            data = resp.json() if resp.ok else {}
            result = data.get('result') or {}
            vals = result.get(pair) or {}
            last = float(vals.get('c', [0])[0] or 0)
            return last
        except Exception:
            return 0.0

    def _fetch_stooq_price(self, symbol):
        sym = symbol.lower() + '.us'
        url = f"https://stooq.com/q/l/?s={sym}&i=d"
        try:
            resp = requests.get(url, timeout=6)
            if not resp.ok:
                return 0.0
            lines = resp.text.strip().splitlines()
            if len(lines) < 2:
                return 0.0
            parts = lines[1].split(',')
            if len(parts) < 5:
                return 0.0
            close = float(parts[4] or 0)
            return close
        except Exception:
            return 0.0

    def get_validation_prices(self, symbol, kind):
        cache_key = f"validation:{symbol}"
        now = time.time()
        cached = self.validation_cache.get(cache_key)
        if cached:
            ts, prices = cached
            if now - ts <= self.validation_cache_ttl:
                return prices

        if kind == 'stock':
            prices = {}
            stooq = self._fetch_stooq_price(symbol)
            if stooq > 0:
                prices['stooq'] = stooq
            self.validation_cache[cache_key] = (now, prices)
            return prices

        base = symbol.split("/", 1)[0] if '/' in symbol else symbol.replace('USD', '')
        prices = {}
        if (
            self.use_coinbase_ws
            and self.coinbase_ws_data
            and (now - self.coinbase_ws_last) <= self.coinbase_ws_timeout
        ):
            ws = self.coinbase_ws_data.get(base)
            if isinstance(ws, dict):
                price = float(ws.get("price", 0) or 0)
                if price > 0:
                    prices["coinbase_ws"] = price
        if (
            self.use_binance_ws
            and self.binance_ws_data
            and (now - self.binance_ws_last) <= self.binance_ws_timeout
        ):
            ws = self.binance_ws_data.get(base)
            if isinstance(ws, dict):
                price = float(ws.get("price", 0) or 0)
                if price > 0:
                    prices["binance_ws"] = price
        if (
            self.use_kraken_ws
            and self.kraken_ws_data
            and (now - self.kraken_ws_last) <= self.kraken_ws_timeout
        ):
            ws = self.kraken_ws_data.get(base)
            if isinstance(ws, dict):
                price = float(ws.get("price", 0) or 0)
                if price > 0:
                    prices["kraken_ws"] = price

        cb = self._fetch_coinbase_price(base)
        if cb > 0:
            prices['coinbase'] = cb
            self._record_price(base, cb, "coinbase_rest")
        bn = self._fetch_binance_price(base)
        if bn > 0:
            prices['binance'] = bn
            self._record_price(base, bn, "binance_rest")
        kr = self._fetch_kraken_price(base)
        if kr > 0:
            prices['kraken'] = kr
            self._record_price(base, kr, "kraken_rest")
        self.validation_cache[cache_key] = (now, prices)
        return prices


class HiveCoordinator:
    def __init__(self, alpaca, sse_client=None, wave_scanner=None, market_radar=None, hnc=None):
        self.alpaca = alpaca
        self.sse = sse_client
        self.wave_scanner = wave_scanner
        self.market_radar = market_radar
        self.hnc = hnc
        self.lock = threading.Lock()
        self.wave_lock = threading.Lock()
        self.target_symbol = None
        self.target_kind = None
        self.target_momentum = -999.0
        self.last_update = 0.0
        self.update_interval = 2.0
        self.min_sse_momentum = 0.02
        self.max_spread = 0.5
        self.sse_periods = 10
        self.wave_scan_interval = float(os.getenv("HIVE_WAVE_SCAN_INTERVAL", "120"))
        self.stream_crypto_limit = int(os.getenv("HIVE_STREAM_CRYPTO_LIMIT", "200"))
        self.stream_stock_limit = int(os.getenv("HIVE_STREAM_STOCK_LIMIT", "0"))
        self.wave_crypto_limit = int(os.getenv("HIVE_CRYPTO_TICKER_LIMIT", "200"))
        self.wave_stock_limit = int(os.getenv("HIVE_STOCK_TICKER_LIMIT", "0"))
        self.wave_stock_exchanges = os.getenv("HIVE_STOCK_EXCHANGES", "NYSE,NASDAQ,AMEX,ARCA,BATS,IEX")
        self.skip_equities_universe = os.getenv("HIVE_SKIP_EQUITIES_UNIVERSE", "false").lower() == "true"
        self.crypto_limit_all = os.getenv("HIVE_CRYPTO_LIMIT_ALL", "false").lower() == "true"
        if self.crypto_limit_all:
            self.stream_crypto_limit = 0
            self.wave_crypto_limit = 0
        # Hardcoded Queen defaults (no env overrides)
        self.wave_scan_interval = 1.0
        self.skip_equities_universe = True
        self.crypto_limit_all = True
        self.stream_crypto_limit = 0
        self.wave_crypto_limit = 0
        self.stream_stock_limit = 0
        self.wave_stock_limit = 0
        self.max_spread = 0.30
        self.wave_last_scan = 0.0
        self.wave_scores = {}
        self.wave_momentum = {}
        self.crypto_symbols = []
        self.stock_symbols = []
        self.stream_crypto_symbols = []
        self.stream_stock_symbols = []
        self.asset_universe = []
        self.wave_weight = 0.6
        self.sse_weight = 0.4
        self._stop_event = threading.Event()
        self._wave_thread = None
        self._wave_crypto_cursor = 0
        self._wave_stock_cursor = 0

    def start_services(self):
        self._load_assets()
        if self.sse:
            if self.stream_crypto_symbols:
                self.sse.start_crypto_stream(self.stream_crypto_symbols, trades=True, quotes=True, bars=False)
            if self.stream_stock_symbols:
                self.sse.start_stock_stream(self.stream_stock_symbols, trades=True, quotes=True)
        if self.wave_scanner and not self._wave_thread:
            self._wave_thread = threading.Thread(target=self._wave_scan_loop, daemon=True)
            self._wave_thread.start()

    def stop_services(self):
        self._stop_event.set()
        if self.sse:
            self.sse.stop()

    def _apply_limit(self, items, limit):
        if limit <= 0:
            return items
        return items[:limit]

    def _parse_exchanges(self):
        raw = (self.wave_stock_exchanges or "").strip()
        if not raw:
            return None
        return [part.strip().upper() for part in raw.split(",") if part.strip()]

    def _slice_symbols(self, symbols, limit, cursor_attr):
        if not symbols:
            return []
        if limit <= 0 or limit >= len(symbols):
            setattr(self, cursor_attr, 0)
            return list(symbols)
        cursor = getattr(self, cursor_attr, 0) % len(symbols)
        end = cursor + limit
        if end <= len(symbols):
            subset = symbols[cursor:end]
        else:
            subset = symbols[cursor:] + symbols[:end - len(symbols)]
        setattr(self, cursor_attr, end % len(symbols))
        return subset

    def _load_assets(self):
        crypto_symbols = []
        stock_symbols = []
        try:
            crypto_symbols = self.alpaca.get_tradable_crypto_symbols() or []
        except Exception:
            crypto_symbols = []

        if not self.skip_equities_universe:
            try:
                exchanges = self._parse_exchanges()
                stock_symbols = self.alpaca.get_tradable_stock_symbols(exchanges=exchanges) or []
            except Exception:
                stock_symbols = []

        if not crypto_symbols:
            crypto_symbols = ["SOL/USD", "BTC/USD", "ETH/USD", "AVAX/USD", "DOGE/USD", "XRP/USD"]

        if not stock_symbols and not self.skip_equities_universe:
            stock_symbols = ["AAPL", "MSFT", "NVDA", "AMZN", "TSLA", "GOOGL"]

        self.crypto_symbols = crypto_symbols
        self.stock_symbols = [] if self.skip_equities_universe else stock_symbols
        self.stream_crypto_symbols = self._apply_limit(crypto_symbols, self.stream_crypto_limit)
        self.stream_stock_symbols = [] if self.skip_equities_universe else self._apply_limit(stock_symbols, self.stream_stock_limit)

        assets = []
        for sym in crypto_symbols:
            if sym.endswith("/USD"):
                base = sym.split("/", 1)[0]
            else:
                base = sym
            assets.append({"symbol": sym, "kind": "crypto", "base": base})

        if not self.skip_equities_universe:
            for sym in stock_symbols:
                assets.append({"symbol": sym, "kind": "stock", "base": sym})

        self.asset_universe = assets

    def _build_ticker_cache(self, tickers):
        cache = {}
        for t in tickers or []:
            sym = t.get('symbol')
            if not sym:
                continue
            if '/' not in sym and sym.endswith('USD') and len(sym) > 5:
                sym = f"{sym[:-3]}/USD"
            price = float(t.get('lastPrice', 0) or 0)
            change = float(t.get('priceChangePercent', 0) or 0)
            volume = float(t.get('quoteVolume', 0) or 0)
            cache[sym] = {
                'price': price,
                'lastPrice': price,
                'priceChangePercent': change,
                'change24h': change,
                'volume': volume,
                'quoteVolume': volume,
            }
        return cache

    def _wave_scan_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        scanner = self.wave_scanner

        while not self._stop_event.is_set():
            try:
                if self.market_radar:
                    crypto_bases = [sym.split('/', 1)[0] if '/' in sym else sym.replace('USD', '') for sym in self.crypto_symbols]
                    focus_bases, validation_base = self.market_radar.get_scan_bases(crypto_bases)
                    scan_bases = list(focus_bases)
                    if validation_base and validation_base not in scan_bases:
                        scan_bases.append(validation_base)
                    crypto_symbols = [f"{b}/USD" for b in scan_bases if b]
                    crypto_tickers = self.market_radar.get_free_tickers(scan_bases)
                else:
                    crypto_symbols = self._slice_symbols(self.crypto_symbols, self.wave_crypto_limit, "_wave_crypto_cursor")
                    crypto_tickers = self.alpaca.get_24h_tickers(symbols=crypto_symbols, limit=self.wave_crypto_limit)
                stock_tickers = []
                if not self.skip_equities_universe:
                    stock_symbols = self._slice_symbols(self.stock_symbols, self.wave_stock_limit, "_wave_stock_cursor")
                    stock_tickers = self.alpaca.get_24h_stock_tickers(symbols=stock_symbols, limit=self.wave_stock_limit)
                ticker_cache = self._build_ticker_cache(crypto_tickers + stock_tickers)

                if not scanner.sorted_symbols_az and not self.skip_equities_universe:
                    loop.run_until_complete(scanner.build_universe())

                if not ticker_cache:
                    self._stop_event.wait(self.wave_scan_interval)
                    continue

                filtered_symbols = [(sym, "alpaca") for sym in ticker_cache.keys()]
                if filtered_symbols:
                    scanner.sorted_symbols_az = sorted(filtered_symbols, key=lambda x: x[0].upper())
                    scanner.sorted_symbols_za = list(reversed(scanner.sorted_symbols_az))

                if self.hnc:
                    for sym, data in ticker_cache.items():
                        try:
                            price = float(data.get("price", 0) or 0)
                            change = float(data.get("priceChangePercent", 0) or 0)
                            volume = float(data.get("quoteVolume", 0) or 0)
                        except Exception:
                            continue
                        if price <= 0:
                            continue
                        coherence = min(1.0, 0.5 + abs(change) / 10.0)
                        is_harmonic = abs(change) >= 0.5
                        self.hnc.update_and_analyze(
                            symbol=sym,
                            price=price,
                            frequency=price,
                            momentum=change,
                            coherence=coherence,
                            is_harmonic=is_harmonic,
                            volume=volume,
                        )

                loop.run_until_complete(scanner.full_az_sweep(ticker_cache))
                loop.run_until_complete(scanner.full_za_sweep(ticker_cache))

                wave_scores = {}
                wave_momentum = {}
                for opp in scanner.top_opportunities[:50]:
                    base = opp.base
                    wave_scores[base] = max(wave_scores.get(base, 0), opp.jump_score)
                    wave_momentum[base] = opp.change_24h

                with self.wave_lock:
                    self.wave_scores = wave_scores
                    self.wave_momentum = wave_momentum
                    self.wave_last_scan = time.time()
            except Exception:
                pass

            self._stop_event.wait(self.wave_scan_interval)

    def update_target(self):
        now = time.time()
        if now - self.last_update < self.update_interval:
            return

        with self.wave_lock:
            wave_scores = dict(self.wave_scores)

        crypto_bases = [a['base'] for a in self.asset_universe if a['kind'] == 'crypto']
        crypto_consensus = {}
        focus_bases = set()
        validation_base = None
        if self.market_radar:
            crypto_consensus, focus_bases, validation_base = self.market_radar.get_crypto_consensus(crypto_bases)
        if validation_base:
            focus_bases.add(validation_base)

        best = None
        best_score = -999.0
        best_mom = None

        for asset in self.asset_universe:
            symbol = asset['symbol']
            base = asset['base']

            if asset['kind'] == 'crypto' and focus_bases and base not in focus_bases:
                continue

            sse_mom = None
            spread_ok = True
            if self.sse:
                sse_mom = self.sse.get_momentum(symbol, periods=self.sse_periods)
                quote = self.sse.get_latest_quote(symbol)
                if quote and quote.get('spread_pct', 0) > self.max_spread:
                    spread_ok = False

            wave_score = wave_scores.get(base, 0.0)
            sse_mom_val = sse_mom if sse_mom is not None else 0.0
            radar = crypto_consensus.get(base, {}) if asset['kind'] == 'crypto' else {}
            radar_score = radar.get('avg', 0.0)
            radar_sources = radar.get('sources', 0)

            if not spread_ok:
                continue

            if sse_mom is not None and sse_mom < self.min_sse_momentum and wave_score < 0.7:
                continue

            consensus_boost = 0.2 if radar_sources >= 2 else 0.0
            score = (self.wave_weight * wave_score) + (self.sse_weight * sse_mom_val) + (0.3 * radar_score) + consensus_boost
            if score > best_score:
                best_score = score
                best = asset
                best_mom = sse_mom_val

        with self.lock:
            if best:
                self.target_symbol = best['symbol']
                self.target_kind = best['kind']
                self.target_momentum = best_mom if best_mom is not None else 0.0
                self.target_eta = 0.0
                self.last_update = now

    def get_target(self):
        with self.lock:
            return self.target_symbol, self.target_momentum, self.target_kind
class AggressiveReclaimer:
    def __init__(self):
        print("=" * 40)
        print("   GAIA AGGRESSIVE RECLAIMER - TAKE EVERYTHING")
        print("=" * 40)
        
        from aureon.exchanges.alpaca_client import AlpacaClient
        from aureon.exchanges.alpaca_sse_client import AlpacaSSEClient, SSE_AVAILABLE
        from aureon.scanners.aureon_global_wave_scanner import GlobalWaveScanner
        
        self.binance = None
        self.alpaca = AlpacaClient()
        self.kraken = None
        self.enable_sse = os.getenv("HIVE_ENABLE_SSE", "false").lower() == "true"
        self.sse_client = AlpacaSSEClient() if SSE_AVAILABLE and self.enable_sse else None
        self.wave_scanner = GlobalWaveScanner(alpaca_client=self.alpaca)
        self.market_radar = MarketRadar(self.alpaca)
        if self.market_radar.use_coinbase:
            self.market_radar.get_coinbase_products()
        if not SSE_AVAILABLE and self.enable_sse:
            print("[WARN] sseclient-py not installed. Streaming momentum disabled.")
        
        self.trades = 0
        self.profit = 0.0
        
        # Track our entry prices PER ASSET
        self.entries = {}
        self.state_lock = threading.Lock()
        self.log_lock = threading.Lock()
        self.log_path = os.path.join(os.getcwd(), "hive_log.csv")
        self.log_every = 1
        self.live_log_every = int(os.getenv("HIVE_LIVE_LOG_EVERY", "1"))
        self.cycle_sleep_sec = float(os.getenv("HIVE_CYCLE_SLEEP_SEC", "1"))
        self.trade_every_cycles = int(os.getenv("HIVE_TRADE_EVERY_CYCLES", "1"))
        self.memory_path = os.getenv("HIVE_MEMORY_PATH", os.path.join(os.getcwd(), "queen_memory_snapshot.jsonl"))
        self.store_live_memory = os.getenv("HIVE_STORE_LIVE_MEMORY", "true").lower() == "true"
        self.validation_tolerance_pct = float(os.getenv("HIVE_VALIDATION_TOLERANCE_PCT", "1.0"))
        self.buy_confirmations = int(os.getenv("HIVE_BUY_CONFIRMATIONS", "1"))
        self.window_seconds = float(os.getenv("HIVE_PROFIT_WINDOW_SEC", "10"))
        self.window_target_pct = float(os.getenv("HIVE_TARGET_PNL_PCT", "0.1"))
        self.reality_branches = int(os.getenv("HIVE_REALITY_BRANCHES", "100"))
        self.reality_base_limit = int(os.getenv("HIVE_REALITY_BASE_LIMIT", "30"))
        self.reality_min_valid = int(os.getenv("HIVE_REALITY_MIN_VALID", "2"))
        self.reality_min_change = float(os.getenv("HIVE_REALITY_MIN_CHANGE", "0.05"))
        self.reality_min_change_subsystem = float(os.getenv("HIVE_REALITY_MIN_CHANGE_SUBSYSTEM", "0.55"))
        self.prob_min_score = float(os.getenv("HIVE_PROB_MIN", "0.55"))
        self.prob_sources_min = int(os.getenv("HIVE_PROB_SOURCES_MIN", "1"))
        self.prob_use_ultimate = os.getenv("HIVE_USE_PROB_ULTIMATE", "true").lower() == "true"
        self.prob_use_matrix = os.getenv("HIVE_USE_PROB_MATRIX", "true").lower() == "true"
        self.prob_use_reports = os.getenv("HIVE_USE_PROB_REPORTS", "true").lower() == "true"
        self.prob_use_hnc = os.getenv("HIVE_USE_PROB_HNC", "false").lower() == "true"
        self.prob_gate_required = os.getenv("HIVE_REQUIRE_PROB_GATE", "false").lower() == "true"
        self.require_all_systems = os.getenv("HIVE_REQUIRE_ALL_SYSTEMS", "true").lower() == "true"
        self.require_ws = os.getenv("HIVE_REQUIRE_WS", "true").lower() == "true"
        self.require_sse = os.getenv("HIVE_REQUIRE_SSE", "false").lower() == "true"
        self.min_ws_symbols = int(os.getenv("HIVE_MIN_WS_SYMBOLS", "10"))
        self.require_clear_profit_exit = os.getenv("HIVE_REQUIRE_CLEAR_PROFIT_EXIT", "false").lower() == "true"
        self.min_profit_usd = float(os.getenv("HIVE_MIN_PROFIT_USD", "0.01"))
        self.sell_confirmations_crypto = int(os.getenv("HIVE_SELL_CONFIRMATIONS_CRYPTO", "1"))
        self.sell_confirmations_stock = int(os.getenv("HIVE_SELL_CONFIRMATIONS_STOCK", "1"))
        self.require_sell_validation = os.getenv("HIVE_REQUIRE_SELL_VALIDATION", "false").lower() == "true"
        self.use_barter_score = os.getenv("HIVE_USE_BARTER_SCORE", "false").lower() == "true"
        self.barter_cache_only = os.getenv("HIVE_BARTER_CACHE_ONLY", "true").lower() == "true"
        self.use_ladder = os.getenv("HIVE_USE_LADDER", "true").lower() == "true"
        self.momentum_min = float(os.getenv("HIVE_MOMENTUM_MIN", "0.0"))
        self.exit_on_positive = os.getenv("HIVE_EXIT_ON_POSITIVE", "true").lower() == "true"
        self.quick_exit_pnl_pct = float(os.getenv("HIVE_QUICK_EXIT_PNL_PCT", "0.0"))
        self.exit_fee_pct = float(os.getenv("HIVE_FEE_PCT", "0.0"))
        self.maker_fee_pct = 0.15
        self.taker_fee_pct = 0.25
        self.fee_buffer_pct = 0.01
        self.exit_slippage_pct = float(os.getenv("HIVE_SLIPPAGE_PCT", "0.02"))
        self.exit_extra_pct = float(os.getenv("HIVE_EXTRA_EXIT_PCT", "0.05"))
        self.sell_buffer_pct = float(os.getenv("HIVE_SELL_BUFFER_PCT", "0.5"))
        self.batch_count = int(os.getenv("HIVE_BATCH_COUNT", "10"))
        self.batch_size = int(os.getenv("HIVE_BATCH_SIZE", "50"))
        self.batch_winners = int(os.getenv("HIVE_BATCH_WINNERS", "3"))
        self.min_trade_usd = float(os.getenv("HIVE_MIN_TRADE_USD", "5.5"))
        self.max_trade_usd = float(os.getenv("HIVE_MAX_TRADE_USD", "10.0"))
        self.max_positions_total = int(os.getenv("HIVE_MAX_POSITIONS", "10"))
        self.max_daily_loss_usd = float(os.getenv("HIVE_MAX_DAILY_LOSS_USD", "0.0"))
        self.require_live_confirmations = os.getenv("HIVE_REQUIRE_LIVE_CONFIRMATIONS", "true").lower() == "true"
        self.live_confirmations_required = int(os.getenv("HIVE_LIVE_CONFIRMATIONS_REQUIRED", "2"))
        self.live_confirm_tolerance_pct = float(
            os.getenv("HIVE_LIVE_CONFIRM_TOLERANCE_PCT", str(self.validation_tolerance_pct))
        )
        self.use_bridge = os.getenv("HIVE_USE_BRIDGE", "true").lower() == "true"
        self.use_thought_bus = os.getenv("HIVE_USE_THOUGHT_BUS", "true").lower() == "true"
        self.use_mycelium = os.getenv("HIVE_USE_MYCELIUM", "true").lower() == "true"
        self.enable_market_pulse = os.getenv("HIVE_ENABLE_MARKET_PULSE", "true").lower() == "true"
        self.enable_lattice = os.getenv("HIVE_ENABLE_LATTICE", "true").lower() == "true"
        self.enable_luck_field = os.getenv("HIVE_ENABLE_LUCK_FIELD", "true").lower() == "true"
        self.enable_whale_sonar = os.getenv("HIVE_ENABLE_WHALE_SONAR", "true").lower() == "true"
        self.market_pulse_interval = float(os.getenv("HIVE_MARKET_PULSE_INTERVAL", "30"))
        self.lattice_interval = float(os.getenv("HIVE_LATTICE_INTERVAL", "5"))
        self.luck_field_interval = float(os.getenv("HIVE_LUCK_FIELD_INTERVAL", "5"))
        self.whale_sonar_interval = float(os.getenv("HIVE_WHALE_SONAR_INTERVAL", "2"))
        self.bridge_owner = os.getenv("HIVE_BRIDGE_OWNER", "gaia")
        self.pnl_history = {}
        self.last_buy = {}
        self.last_positions_summary = []
        self.last_reality = None
        self.last_validation = {}
        self.last_account = {}
        self.last_cash_warn_ts = 0.0
        self.last_ladder = {}
        self.last_orders = []
        self.last_bridge_status = {}
        self.last_activity_summary = {}
        self.activity_fee_pct = 0.0
        self.activity_fee_last = 0.0
        self.last_buy_blocker = ""
        self.activity_fee_interval = float(os.getenv("HIVE_ACTIVITY_FEE_INTERVAL", "30"))
        self.sim_validation = {}
        self.sim_validation_ttl = 10.0
        self.sim_count = 1000
        self.sim_window_sec = 3600.0
        self.sim_lookback_sec = 3600.0
        self.sim_scoreboard = {}
        # Allow override of how many simulated wins are required before buying; default relaxed to 1
        self.sim_required_wins = int(os.getenv("HIVE_SIM_REQUIRED_WINS", "1"))
        self.prob_live_window_sec = 3600.0
        self.prob_projection_sec = 3600.0
        self.stop_on_first_profit = True
        self._halt_after_profit = False
        self.force_execute_on_scoreboard = True
        self.daily_start_equity = None
        self.daily_date = None
        self.daily_pnl = 0.0
        self.trading_halted = False
        self.trading_halt_reason = ""
        self._positions_cache = []
        self._positions_cache_ts = 0.0
        self._positions_cache_ttl = 1.0
        self._account_cache = {}
        self._account_cache_ts = 0.0
        self._account_cache_ttl = 1.0
        self._quote_cache = {}
        self._quote_cache_ts = {}
        self._quote_cache_ttl = 1.0
        self._orderbook_cache = {}
        self._orderbook_cache_ts = {}
        self._orderbook_cache_ttl = 1.0
        self.orderbook_depth_levels = 3
        self.orderbook_min_depth_usd = 20.0
        self.analytics_loop_interval = 2.5
        self._analytics_thread = None
        self._analytics_stop = threading.Event()
        self.last_momentum_analytics = {}
        self.analytics_cache = {}
        self.analytics_last_ts = {}
        self.last_orders_ts = 0.0
        self.order_sync_interval = float(os.getenv("HIVE_ORDER_SYNC_INTERVAL", "10"))
        self.dash_heartbeat_path = os.getenv("HIVE_DASH_HEARTBEAT_PATH", os.path.join(os.getcwd(), "dashboard_heartbeat.json"))
        self.bridge_dir = os.getenv("HIVE_BRIDGE_DIR", os.path.join(os.getcwd(), "memory", "bridge"))
        if self.use_bridge:
            try:
                os.makedirs(self.bridge_dir, exist_ok=True)
            except Exception:
                pass
        self.bridge = AureonBridge(self.bridge_dir) if self.use_bridge and AureonBridge else None
        self.thought_bus = get_thought_bus(os.getenv("HIVE_THOUGHT_BUS_PATH", "thoughts.jsonl")) if self.use_thought_bus and get_thought_bus else None
        self.mycelium = get_mycelium(initial_capital=100.0) if self.use_mycelium and get_mycelium else None
        self.whale_sonar = None
        if self.enable_whale_sonar and self.thought_bus and ensure_sonar:
            try:
                self.whale_sonar = ensure_sonar(self.thought_bus)
            except Exception:
                self.whale_sonar = None
        self.market_pulse_client = None
        self.market_pulse = None
        if self.enable_market_pulse and MarketPulse:
            use_multi = os.getenv("HIVE_MARKET_PULSE_MULTI", "true").lower() == "true"
            if use_multi and MultiExchangeClient:
                try:
                    self.market_pulse_client = MultiExchangeClient()
                except Exception:
                    self.market_pulse_client = None
            if not self.market_pulse_client:
                self.market_pulse_client = self.alpaca
            try:
                self.market_pulse = MarketPulse(self.market_pulse_client)
            except Exception:
                self.market_pulse = None
        self.lattice = None
        if self.enable_lattice and LatticeEngine:
            try:
                self.lattice = LatticeEngine()
            except Exception:
                self.lattice = None
        self.luck_mapper = None
        if self.enable_luck_field and get_luck_mapper:
            try:
                self.luck_mapper = get_luck_mapper()
            except Exception:
                self.luck_mapper = None
        self._auris_engine = AurisEngine() if AurisEngine else None
        self._harmonic_analyzer = HarmonicAnalyzer() if HarmonicAnalyzer else None
        self._mean_reversion = MeanReversionDetector() if MeanReversionDetector else None
        self._phase_aligner = PhaseAligner() if PhaseAligner else None
        self._prob_matrix = ProbabilityMatrix() if ProbabilityMatrix else None
        self._subsystem_cache = {}
        self._subsystem_cache_ttl = float(os.getenv("HIVE_SUBSYSTEM_CACHE_TTL", "2"))
        self._subsystem_weight = float(os.getenv("HIVE_SUBSYSTEM_WEIGHT", "0.4"))
        self._subsystem_min_score = float(os.getenv("HIVE_SUBSYSTEM_MIN_SCORE", "0"))
        self._subsystem_debug = os.getenv("HIVE_SUBSYSTEM_DEBUG", "false").lower() == "true"
        self.compound_checkpoints = self._parse_compound_checkpoints(
            os.getenv("HIVE_COMPOUND_CHECKPOINTS", "0.03,0.05,0.08,0.13,0.21,0.34,0.55")
        )
        self.compound_index = 0
        self.compound_auto_expand = os.getenv("HIVE_COMPOUND_AUTO_EXPAND", "true").lower() == "true"
        self.compound_multiplier = float(os.getenv("HIVE_COMPOUND_MULTIPLIER", "1.618"))
        self._prob_loader = ProbabilityLoader(os.getcwd()) if ProbabilityLoader and self.prob_use_reports else None
        self._prob_loader_last = 0.0
        self._hnc = HNCProbabilityIntegration() if HNCProbabilityIntegration and self.prob_use_hnc else None
        self.ladder = None
        if self.use_ladder and ConversionLadder:
            self.ladder = ConversionLadder(bus=None, mycelium=None, client=None)
            self.ladder.enabled = True
            self.ladder.mode = "suggest"
            self.ladder.cooldown_s = float(os.getenv("HIVE_LADDER_COOLDOWN_S", "5"))
        self.coordinator = HiveCoordinator(self.alpaca, self.sse_client, self.wave_scanner, self.market_radar, self._hnc)
        self.enable_lion = os.getenv("HIVE_ENABLE_LION", "true").lower() == "true"
        self._lion_cache = {}
        self._lion_cache_ttl = float(os.getenv("HIVE_LION_CACHE_TTL", "5"))
        self._lion_weight = float(os.getenv("HIVE_LION_WEIGHT", "0.2"))
        # Hardcoded Queen defaults (no env overrides)
        self.cycle_sleep_sec = 0.25
        self.trade_every_cycles = 1
        self.enable_market_pulse = False
        self.require_all_systems = False
        self.require_ws = False
        self.require_sse = False
        self.require_live_confirmations = False
        self.buy_confirmations = 0
        self.prob_gate_required = False
        self.require_sell_validation = False
        self.require_clear_profit_exit = False
        self.min_trade_usd = 0.25
        self.max_trade_usd = 10.0
        self.max_positions_total = 10
        self.min_profit_usd = 0.0175
        self.quick_exit_pnl_pct = 0.0
        self.sell_buffer_pct = 0.10
        self.exit_extra_pct = 0.02
        self.momentum_min = 0.01
        self.reality_min_change = 0.01
        self.fast_money_mode = True
        self.fast_money_eta_sec = 10.0
        self.fast_money_expected_pct = 0.0
        self.min_profit_usd = 0.0
        self.reality_base_limit = 0
        if self.market_radar:
            self.market_radar.price_history_window = 60.0
        self.prob_use_reports = False
        self._prob_loader = None
        self.log_every = 1
        self.live_log_every = 1
        self.coordinator.start_services()
        self._init_log()
        
        print("[OK] ALPACA ONLY - WAVE + SSE SCAN (CRYPTO+STOCKS)")
        print()
        
    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {msg}", flush=True)

    def _get_entry(self, key):
        with self.state_lock:
            return self.entries.get(key)

    def _set_entry(self, key, price):
        with self.state_lock:
            self.entries[key] = price

    def _del_entry(self, key):
        with self.state_lock:
            if key in self.entries:
                del self.entries[key]

    def _add_trade_profit(self, profit_usd):
        with self.state_lock:
            self.profit += profit_usd
            self.trades += 1
            current_profit = self.profit
        if self.bridge:
            try:
                # Use penny-profit threshold for success (unify with QUEEN policy)
                self.bridge.record_trade(profit=profit_usd, fee=0.0, success=(profit_usd >= 0.01))
            except Exception:
                pass
        if self.mycelium and hasattr(self.mycelium, "record_trade_profit"):
            try:
                self.mycelium.record_trade_profit(profit_usd, {"source": "gaia"})
            except Exception:
                pass
        self._check_compound_checkpoint(current_profit)

    def _parse_compound_checkpoints(self, raw):
        items = []
        for part in (raw or "").split(","):
            part = part.strip()
            if not part:
                continue
            try:
                value = float(part)
            except Exception:
                continue
            if value > 0:
                items.append(value)
        return sorted(set(items))

    def _check_compound_checkpoint(self, profit_total):
        if not self.compound_checkpoints:
            return
        while self.compound_index < len(self.compound_checkpoints):
            target = self.compound_checkpoints[self.compound_index]
            if profit_total + 1e-9 < target:
                break
            payload = {
                "ts": datetime.now().isoformat(),
                "event": "compound_checkpoint",
                "level": self.compound_index + 1,
                "target_usd": target,
                "profit_total": profit_total,
            }
            self._write_queen_memory(payload)
            self.compound_index += 1
            if self.compound_auto_expand and self.compound_index >= len(self.compound_checkpoints):
                last_target = self.compound_checkpoints[-1]
                next_target = last_target * max(1.01, self.compound_multiplier)
                self.compound_checkpoints.append(round(next_target, 6))

    def _should_buy(self, momentum):
        try:
            mom = float(momentum or 0.0)
        except Exception:
            mom = 0.0
        if mom < self.momentum_min:
            return False, f"momentum_below_min({mom:+.2f}<{self.momentum_min:+.2f})"
        return True, "momentum_ok"

    def _estimate_exit_threshold(self, symbol, kind):
        spread_pct = 0.0
        if self.sse_client:
            try:
                quote = self.sse_client.get_latest_quote(symbol)
                spread_pct = float(quote.get("spread_pct", 0) or 0)
            except Exception:
                spread_pct = 0.0
        fee_pct = self.taker_fee_pct
        if fee_pct <= 0 and self.exit_fee_pct > 0:
            fee_pct = self.exit_fee_pct
        activity_component = self.activity_fee_pct
        if self.activity_fee_pct > 0:
            fee_pct = self.activity_fee_pct
            activity_component = 0.0
        total = (
            fee_pct
            + self.exit_slippage_pct
            + spread_pct
            + self.exit_extra_pct
            + activity_component
            + self.sell_buffer_pct
            + self.fee_buffer_pct
        )
        return total, {
            "fee_pct": fee_pct,
            "slippage_pct": self.exit_slippage_pct,
            "spread_pct": spread_pct,
            "extra_pct": self.exit_extra_pct,
            "activity_fee_pct": activity_component,
            "buffer_pct": self.sell_buffer_pct,
            "fee_buffer_pct": self.fee_buffer_pct,
            "total_pct": total,
        }

    def _candidate_priority(self, candidate):
        try:
            eta = float(candidate.get("eta_sec", 0) or 0)
        except Exception:
            eta = 0.0
        try:
            score = float(candidate.get("subsystem_score", 0) or 0)
        except Exception:
            score = 0.0
        if eta <= 0:
            eta = 1e-6
        return eta / max(0.5, 0.5 + score)

    def _extract_base_from_symbol(self, symbol):
        sym = (symbol or "").upper()
        for quote in ("USDT", "USDC", "USD", "BTC", "ETH", "BNB"):
            if sym.endswith(quote) and len(sym) > len(quote):
                return sym[: -len(quote)]
        if "/" in sym:
            return sym.split("/", 1)[0]
        return sym

    def _build_lion_client(self, tickers):
        class _LionClient:
            def __init__(self, data):
                self._data = data

            def get_24h_tickers(self):
                return list(self._data or [])

        return _LionClient(tickers)

    def _get_lion_scores(self, bases):
        if not self.enable_lion or not PrideScanner or not LionHunt:
            return {"scores": {}, "best": None}
        if not self.market_radar:
            return {"scores": {}, "best": None}
        now = time.time()
        cached = self._lion_cache.get("lion")
        if cached and now - cached.get("ts", 0) <= self._lion_cache_ttl:
            return cached.get("data", {})

        tickers = []
        try:
            binance = self.market_radar._fetch_binance_24h()
        except Exception:
            binance = {}
        if isinstance(binance, dict):
            for base, data in binance.items():
                if not isinstance(data, dict):
                    continue
                tickers.append(
                    {
                        "symbol": f"{base}USDT",
                        "quoteVolume": float(data.get("volume", 0) or 0),
                        "priceChangePercent": float(data.get("change", 0) or 0),
                        "lastPrice": float(data.get("price", 0) or 0),
                    }
                )
        if not tickers and bases:
            free = self.market_radar.get_free_tickers(bases)
            for t in free or []:
                sym = t.get("symbol", "")
                tickers.append(
                    {
                        "symbol": sym,
                        "quoteVolume": float(t.get("quoteVolume", 0) or t.get("volume", 0) or 0),
                        "priceChangePercent": float(t.get("priceChangePercent", 0) or t.get("change", 0) or 0),
                        "lastPrice": float(t.get("lastPrice", 0) or t.get("price", 0) or 0),
                    }
                )

        if not tickers and bases:
            targets = []
            reality = self._reality_sources(bases) or {}
            for base, data in reality.items():
                change = float(data.get("change", 0) or 0)
                price = float(data.get("price", 0) or 0)
                volume_usd = float(data.get("volume", 0) or 0)
                if volume_usd <= 0 and price > 0:
                    volume_usd = max(1.0, price * 10.0)
                opportunity = (volume_usd / 1000000.0) * abs(change)
                targets.append(
                    {
                        "symbol": f"{base}USDT",
                        "volume_usd": volume_usd,
                        "change_pct": change,
                        "opportunity_score": opportunity,
                        "price": price,
                    }
                )
            targets.sort(key=lambda x: x.get("opportunity_score", 0), reverse=True)
            best = targets[0] if targets else None
            scores = {}
            max_score = targets[0]["opportunity_score"] if targets else 0.0
            for target in targets:
                base = self._extract_base_from_symbol(target.get("symbol"))
                if bases and base not in bases:
                    continue
                try:
                    score = float(target.get("opportunity_score", 0) or 0)
                except Exception:
                    score = 0.0
                norm = score / max_score if max_score > 0 else 0.0
                scores[base] = min(1.0, max(0.0, norm))
            data = {"scores": scores, "best": best}
            self._lion_cache["lion"] = {"ts": now, "data": data}
            return data

        client = self._build_lion_client(tickers)
        scanner = PrideScanner(client)
        hunter = LionHunt(client, scanner)
        targets = scanner.scan_pride(
            min_volume_usd=float(os.getenv("HIVE_LION_MIN_VOLUME_USD", "20000")),
            min_volatility=float(os.getenv("HIVE_LION_MIN_VOLATILITY", "0.5")),
        )
        best = hunter.select_prey(targets)
        scores = {}
        max_score = targets[0]["opportunity_score"] if targets else 0.0
        for target in targets:
            base = self._extract_base_from_symbol(target.get("symbol"))
            if bases and base not in bases:
                continue
            try:
                score = float(target.get("opportunity_score", 0) or 0)
            except Exception:
                score = 0.0
            norm = score / max_score if max_score > 0 else 0.0
            scores[base] = min(1.0, max(0.0, norm))

        data = {"scores": scores, "best": best}
        self._lion_cache["lion"] = {"ts": now, "data": data}
        return data

    def _compute_subsystem_scores(self, base, symbol, price, change, volume, prob_score, lion_score=None):
        now = time.time()
        cache_key = f"{base}:{symbol}"
        cached = self._subsystem_cache.get(cache_key)
        if cached and now - cached.get("ts", 0) <= self._subsystem_cache_ttl:
            return cached.get("data", {})

        prices = []
        if self.market_radar:
            history = self.market_radar.get_price_history(base, limit=120)
            prices = [h.get("price") for h in history if h.get("price")]

        returns = []
        if len(prices) >= 2:
            for i in range(1, len(prices)):
                p0 = prices[i - 1]
                p1 = prices[i]
                if p0 > 0:
                    returns.append((p1 - p0) / p0)

        volatility_pct = 0.0
        if returns:
            try:
                volatility_pct = statistics.pstdev(returns) * 100.0
            except Exception:
                volatility_pct = 0.0
        volatility_norm = min(1.0, volatility_pct / 2.0) if volatility_pct > 0 else 0.2

        try:
            volume_norm = min(1.0, float(volume or 0) / 10000000.0)
        except Exception:
            volume_norm = 0.0
        try:
            momentum_norm = max(-1.0, min(1.0, float(change or 0) / 5.0))
        except Exception:
            momentum_norm = 0.0
        spread_norm = 0.2

        coherence_score = None
        if self._auris_engine and MarketSnapshot:
            try:
                snapshot = MarketSnapshot(
                    symbol=symbol,
                    price=float(price or 0),
                    volume=volume_norm,
                    volatility=volatility_norm,
                    momentum=momentum_norm,
                    spread=spread_norm,
                    timestamp=now,
                )
                coherence_score = float(self._auris_engine.calculate_coherence(snapshot))
            except Exception:
                coherence_score = None
        if coherence_score is None:
            coherence_score = max(0.0, min(1.0, 0.5 + (momentum_norm * 0.1) - (volatility_norm * 0.1)))

        harmonic_score = None
        harmonic_meta = {}
        phase_val = None
        if self._harmonic_analyzer and prices:
            try:
                freq, coh, phase = self._harmonic_analyzer.analyze(prices)
                harmonic_score = float(self._harmonic_analyzer.get_frequency_probability(freq))
                harmonic_meta = {"frequency": float(freq), "coherence": float(coh), "phase": float(phase)}
                phase_val = float(phase)
            except Exception:
                harmonic_score = None
        if harmonic_score is None and calculate_golden_ratio_alignment and prices:
            try:
                harmonic_score = float(calculate_golden_ratio_alignment(prices))
            except Exception:
                harmonic_score = None
        if harmonic_score is None:
            harmonic_score = 0.5

        phase_score = None
        if phase_val is None and prices:
            try:
                low = min(prices)
                high = max(prices)
                if high > low:
                    position = (prices[-1] - low) / (high - low)
                    phase_val = position * (2 * math.pi)
            except Exception:
                phase_val = None
        if self._phase_aligner and phase_val is not None:
            try:
                phase_score = float(self._phase_aligner.get_phase_score(phase_val, "LONG"))
            except Exception:
                phase_score = None
        if phase_score is None:
            phase_score = 0.5

        meanrev_score = None
        momentum_6 = None
        if returns:
            recent = returns[-6:]
            momentum_6 = sum(1 for r in recent if r > 0)
        if self._mean_reversion and momentum_6 is not None:
            try:
                meanrev_score = float(self._mean_reversion.get_reversal_bias(momentum_6))
            except Exception:
                meanrev_score = None
        if meanrev_score is None:
            if momentum_6 is None:
                meanrev_score = 0.5
            elif momentum_6 <= 1:
                meanrev_score = 0.53
            elif momentum_6 >= 5:
                meanrev_score = 0.47
            else:
                meanrev_score = 0.5

        prob_subscore = None
        if prob_score is not None:
            try:
                prob_subscore = max(0.0, min(1.0, float(prob_score)))
            except Exception:
                prob_subscore = None
        if prob_subscore is None:
            prob_subscore = 0.5

        subscores = {
            "harmonic": harmonic_score,
            "coherence": coherence_score,
            "probability": prob_subscore,
            "meanrev": meanrev_score,
            "phase": phase_score,
        }
        if lion_score is not None:
            try:
                subscores["lion"] = max(0.0, min(1.0, float(lion_score)))
            except Exception:
                subscores["lion"] = 0.5
        valid = [v for v in subscores.values() if isinstance(v, (int, float))]
        subsystem_score = sum(valid) / len(valid) if valid else 0.5
        data = {
            "score": subsystem_score,
            "scores": subscores,
            "meta": harmonic_meta,
        }
        self._subsystem_cache[cache_key] = {"ts": now, "data": data}
        return data

    def _estimate_eta_from_pnl(self, symbol, pnl_pct, target_pct, lookback_sec=1.0):
        if not self.market_radar:
            return None
        base = self._normalize_base(symbol)
        history = self.market_radar.get_price_history(base, limit=120, window_sec=lookback_sec)
        if len(history) < 2:
            return None
        first = history[0]
        last = history[-1]
        dt = max(1e-6, float(last["ts"]) - float(first["ts"]))
        p0 = float(first["price"] or 0)
        p1 = float(last["price"] or 0)
        if p0 <= 0 or p1 <= 0:
            return None
        pct_move = (p1 - p0) / p0 * 100.0
        slope = pct_move / dt
        if slope <= 0:
            return None
        remaining = float(target_pct or 0) - float(pnl_pct or 0)
        if remaining <= 0:
            return 0.0
        return remaining / slope

    def _should_sell(self, pnl_pct, profit_usd, symbol, kind):
        try:
            pnl_val = float(pnl_pct or 0.0)
        except Exception:
            pnl_val = 0.0
        try:
            profit_val = float(profit_usd or 0.0)
        except Exception:
            profit_val = 0.0
        if self.fast_money_mode and profit_val > 0:
            return True, "fast_money_profit"
        if self.exit_on_positive:
            if pnl_val <= 0:
                return False, "pnl_not_positive"
            if pnl_val < self.quick_exit_pnl_pct:
                return False, "pnl_below_quick_exit"
            threshold, meta = self._estimate_exit_threshold(symbol, kind)
            if pnl_val < threshold:
                return False, f"pnl_below_costs({pnl_val:.2f}<{threshold:.2f})"
            value_est = 0.0
            if pnl_val > 0:
                value_est = profit_val / (pnl_val / 100.0)
            required_profit = (value_est * (threshold / 100.0)) + self.min_profit_usd if value_est > 0 else self.min_profit_usd
            if profit_val < required_profit:
                return False, "profit_below_costs_plus_penny"
            return True, "exit_on_positive"
        return False, "exit_disabled"

    def _queen_logic_summary(self, target_symbol, target_mom, target_kind, decision_note=""):
        threshold, meta = self._estimate_exit_threshold(target_symbol or "", target_kind or "crypto")
        return {
            "ts": datetime.now().isoformat(),
            "target": target_symbol,
            "momentum": target_mom,
            "momentum_min": self.momentum_min,
            "exit_on_positive": self.exit_on_positive,
            "quick_exit_pnl_pct": self.quick_exit_pnl_pct,
            "min_profit_usd": self.min_profit_usd,
            "exit_threshold_pct": threshold,
            "exit_meta": meta,
            "decision_note": decision_note,
            "mycelium": self._mycelium_snapshot(),
            "analytics": self.last_momentum_analytics or {},
            "risk_controls": {
                "min_trade_usd": self.min_trade_usd,
                "max_trade_usd": self.max_trade_usd,
                "max_positions_total": self.max_positions_total,
                "max_daily_loss_usd": self.max_daily_loss_usd,
                "require_live_confirmations": self.require_live_confirmations,
                "live_confirmations_required": self.live_confirmations_required,
                "daily_pnl": self.daily_pnl,
                "trading_halted": self.trading_halted,
                "halt_reason": self.trading_halt_reason,
            },
        }

    def _normalize_symbol(self, symbol):
        sym = (symbol or '').upper().strip()
        if '/' in sym:
            return sym
        if sym.endswith('USD') and len(sym) > 5:
            base = sym[:-3]
            return f"{base}/USD"
        return sym

    def _symbol_kind(self, symbol):
        sym = self._normalize_symbol(symbol)
        if '/' in sym:
            return 'crypto'
        return 'stock'

    def _get_latest_price(self, symbol, kind):
        try:
            now = time.time()
            cache_ts = self._quote_cache_ts.get(symbol, 0.0)
            if now - cache_ts <= self._quote_cache_ttl:
                cached = self._quote_cache.get(symbol)
                if cached:
                    return cached
            if kind == 'crypto':
                quotes = self.alpaca.get_latest_crypto_quotes([symbol]) or {}
                q = quotes.get(symbol, {})
                ap = float(q.get('ap', 0) or 0)
                bp = float(q.get('bp', 0) or 0)
                if ap > 0 and bp > 0:
                    price = (ap + bp) / 2
                else:
                    price = ap or bp or 0.0
                if price > 0:
                    self._quote_cache[symbol] = price
                    self._quote_cache_ts[symbol] = now
                return price
            quote = self.alpaca.get_last_quote(symbol)
            price = float(quote.get('last', {}).get('price', 0) or 0)
            if price > 0:
                self._quote_cache[symbol] = price
                self._quote_cache_ts[symbol] = now
            return price
        except Exception:
            return 0.0

    def _prime_crypto_quote_cache(self, symbols):
        if not symbols:
            return
        try:
            quotes = self.alpaca.get_latest_crypto_quotes(symbols) or {}
        except Exception:
            return
        now = time.time()
        for sym, q in quotes.items():
            try:
                ap = float(q.get("ap", 0) or 0)
                bp = float(q.get("bp", 0) or 0)
            except Exception:
                continue
            if ap > 0 and bp > 0:
                price = (ap + bp) / 2
            else:
                price = ap or bp or 0.0
            if price > 0:
                self._quote_cache[sym] = price
                self._quote_cache_ts[sym] = now

    def _get_positions_cached(self):
        now = time.time()
        if now - self._positions_cache_ts <= self._positions_cache_ttl:
            return list(self._positions_cache)
        try:
            positions = self.alpaca.get_positions() or []
        except Exception:
            return []
        self._positions_cache = positions
        self._positions_cache_ts = now
        return list(positions)

    def _get_account_cached(self):
        now = time.time()
        if now - self._account_cache_ts <= self._account_cache_ttl:
            return dict(self._account_cache)
        try:
            acc = self.alpaca.get_account() or {}
        except Exception:
            return {}
        self._account_cache = acc
        self._account_cache_ts = now
        return dict(acc)

    def _parse_orderbook_side(self, side):
        levels = []
        for level in side or []:
            price = 0.0
            size = 0.0
            if isinstance(level, dict):
                price = float(level.get("p") or level.get("price") or level.get("bp") or 0)
                size = float(level.get("s") or level.get("size") or level.get("q") or 0)
            elif isinstance(level, (list, tuple)) and len(level) >= 2:
                try:
                    price = float(level[0])
                    size = float(level[1])
                except Exception:
                    price = 0.0
                    size = 0.0
            if price > 0 and size > 0:
                levels.append((price, size))
        return levels

    def _get_orderbook_metrics(self, symbol):
        now = time.time()
        cache_ts = self._orderbook_cache_ts.get(symbol, 0.0)
        if now - cache_ts <= self._orderbook_cache_ttl:
            return self._orderbook_cache.get(symbol)
        try:
            book = self.alpaca.get_crypto_orderbook(symbol, depth=self.orderbook_depth_levels) or {}
        except Exception:
            return None
        bids = self._parse_orderbook_side(book.get("bids") or [])
        asks = self._parse_orderbook_side(book.get("asks") or [])
        if not bids or not asks:
            return None
        best_bid = bids[0][0]
        best_ask = asks[0][0]
        mid = (best_bid + best_ask) / 2 if best_bid > 0 and best_ask > 0 else 0.0
        spread_pct = ((best_ask - best_bid) / mid * 100.0) if mid > 0 else 0.0
        bid_depth_usd = sum(p * s for p, s in bids[: self.orderbook_depth_levels])
        ask_depth_usd = sum(p * s for p, s in asks[: self.orderbook_depth_levels])
        metrics = {
            "best_bid": best_bid,
            "best_ask": best_ask,
            "spread_pct": spread_pct,
            "bid_depth_usd": bid_depth_usd,
            "ask_depth_usd": ask_depth_usd,
        }
        self._orderbook_cache[symbol] = metrics
        self._orderbook_cache_ts[symbol] = now
        return metrics

    def _validate_sell_price(self, symbol, entry_price, is_target, kind, skip_delay=False):
        if not skip_delay:
            time.sleep(0.0)
        price = self._get_latest_price(symbol, kind)
        if price <= 0:
            return False, 0.0

        pnl_pct = (price - entry_price) / entry_price * 100 if entry_price > 0 else 0.0
        if is_target and pnl_pct <= 0.0:
            return False, pnl_pct
        if not is_target and pnl_pct < 0.0:
            return False, pnl_pct

        if kind == 'stock':
            required = self.sell_confirmations_stock
        else:
            required = self.sell_confirmations_crypto
        if self.market_radar and self.require_sell_validation:
            prices = self.market_radar.get_validation_prices(symbol, kind)
            confirmations = 0
            for src_price in prices.values():
                if src_price > 0:
                    diff = abs(price - src_price) / price * 100
                    if diff <= self.validation_tolerance_pct:
                        confirmations += 1
            if confirmations < required:
                self.last_validation = {
                    "ts": datetime.now().isoformat(),
                    "type": "sell",
                    "symbol": symbol,
                    "confirmations": confirmations,
                    "required": required,
                    "price": price,
                    "pnl_pct": pnl_pct,
                }
                return False, pnl_pct

            self.last_validation = {
                "ts": datetime.now().isoformat(),
                "type": "sell",
                "symbol": symbol,
                "confirmations": confirmations,
                "required": required,
                "price": price,
                "pnl_pct": pnl_pct,
            }

        if kind == "crypto":
            ob = self._get_orderbook_metrics(symbol)
            if ob:
                min_depth = max(self.orderbook_min_depth_usd, self.min_trade_usd * 2.0)
                if ob.get("spread_pct", 0) > self.max_spread:
                    self.last_validation = {
                        "ts": datetime.now().isoformat(),
                        "type": "sell_orderbook",
                        "symbol": symbol,
                        "confirmations": 0,
                        "required": 1,
                        "price": price,
                        "pnl_pct": pnl_pct,
                        "orderbook": ob,
                        "reason": "spread_too_wide",
                    }
                    return False, pnl_pct
                if ob.get("bid_depth_usd", 0) < min_depth:
                    self.last_validation = {
                        "ts": datetime.now().isoformat(),
                        "type": "sell_orderbook",
                        "symbol": symbol,
                        "confirmations": 0,
                        "required": 1,
                        "price": price,
                        "pnl_pct": pnl_pct,
                        "orderbook": ob,
                        "reason": "bid_depth_low",
                    }
                    return False, pnl_pct

        if self.require_live_confirmations:
            confirmations, prices, alpaca_price = self._live_confirmations(symbol, kind)
            if confirmations < self.live_confirmations_required:
                self.last_validation = {
                    "ts": datetime.now().isoformat(),
                    "type": "sell_live",
                    "symbol": symbol,
                    "confirmations": confirmations,
                    "required": self.live_confirmations_required,
                    "price": alpaca_price,
                    "pnl_pct": pnl_pct,
                    "sources": list(prices.keys()),
                }
                return False, pnl_pct
        return True, pnl_pct

    def _validate_buy_price(self, symbol, kind):
        price = self._get_latest_price(symbol, kind)
        if price <= 0:
            return False, 0, {}

        if not self.market_radar:
            return True, 0, {}

        prices = self.market_radar.get_validation_prices(symbol, kind)
        confirmations = 0
        for src_price in prices.values():
            if src_price > 0:
                diff = abs(price - src_price) / price * 100
                if diff <= self.validation_tolerance_pct:
                    confirmations += 1
        self.last_validation = {
            "ts": datetime.now().isoformat(),
            "type": "buy",
            "symbol": symbol,
            "confirmations": confirmations,
            "required": self.buy_confirmations,
            "price": price,
        }
        if confirmations < self.buy_confirmations:
            self.last_buy_blocker = f"validation {confirmations}/{self.buy_confirmations}"
        if self.buy_confirmations <= 0:
            return True, confirmations, prices
        if confirmations < self.buy_confirmations:
            return False, confirmations, prices

        if kind == "crypto":
            ob = self._get_orderbook_metrics(symbol)
            if ob:
                min_depth = max(self.orderbook_min_depth_usd, self.min_trade_usd * 2.0)
                if ob.get("spread_pct", 0) > self.max_spread:
                    self.last_validation = {
                        "ts": datetime.now().isoformat(),
                        "type": "buy_orderbook",
                        "symbol": symbol,
                        "confirmations": confirmations,
                        "required": self.buy_confirmations,
                        "price": price,
                        "orderbook": ob,
                        "reason": "spread_too_wide",
                    }
                    self.last_buy_blocker = "orderbook_spread"
                    return False, confirmations, prices
                if ob.get("ask_depth_usd", 0) < min_depth:
                    self.last_validation = {
                        "ts": datetime.now().isoformat(),
                        "type": "buy_orderbook",
                        "symbol": symbol,
                        "confirmations": confirmations,
                        "required": self.buy_confirmations,
                        "price": price,
                        "orderbook": ob,
                        "reason": "ask_depth_low",
                    }
                    self.last_buy_blocker = "orderbook_depth"
                    return False, confirmations, prices

        if self.require_live_confirmations:
            live_confirmations, live_prices, alpaca_price = self._live_confirmations(symbol, kind)
            if live_confirmations < self.live_confirmations_required:
                self.last_validation = {
                    "ts": datetime.now().isoformat(),
                    "type": "buy_live",
                    "symbol": symbol,
                    "confirmations": live_confirmations,
                    "required": self.live_confirmations_required,
                    "price": alpaca_price,
                    "sources": list(live_prices.keys()),
                }
                self.last_buy_blocker = "live_confirmations"
                return False, live_confirmations, live_prices
        return True, confirmations, prices

    def _update_pnl_history(self, symbol, pnl_pct):
        now = time.time()
        history = self.pnl_history.get(symbol, [])
        history.append((now, pnl_pct))
        cutoff = now - max(self.window_seconds * 2, 30)
        history = [(ts, pnl) for ts, pnl in history if ts >= cutoff]
        self.pnl_history[symbol] = history
        return history

    def _normalize_base(self, symbol):
        sym = (symbol or "").upper().strip()
        if "/" in sym:
            return sym.split("/", 1)[0]
        if sym.endswith("USD") and len(sym) > 5:
            return sym[:-3]
        return sym

    def _compute_volatility(self, prices):
        if not prices or len(prices) < 2:
            return 0.5
        returns = []
        for idx in range(1, len(prices)):
            p0 = prices[idx - 1]
            p1 = prices[idx]
            if p0 <= 0 or p1 <= 0:
                continue
            returns.append((p1 - p0) / p0)
        if not returns:
            return 0.5
        try:
            vol = statistics.pstdev(returns)
        except Exception:
            vol = 0.0
        return max(0.0, min(1.0, vol * 20.0))

    def _build_lattice_opportunities(self):
        opportunities = []
        if self.wave_scanner and getattr(self.wave_scanner, "top_opportunities", None):
            for opp in list(self.wave_scanner.top_opportunities)[:50]:
                try:
                    coherence = float(getattr(opp, "wave_strength", 0) or 0)
                    change = float(getattr(opp, "change_24h", 0) or 0)
                except Exception:
                    coherence = 0.0
                    change = 0.0
                opportunities.append({"coherence": coherence, "change24h": change})
            return opportunities
        if self.market_radar:
            consensus = self.market_radar.last_consensus or {}
            for base, entry in consensus.items():
                try:
                    change = float(entry.get("avg", 0) or 0)
                except Exception:
                    change = 0.0
                coherence = min(1.0, abs(change) / 5.0)
                opportunities.append({"coherence": coherence, "change24h": change})
        return opportunities

    def _summarize_market_pulse(self, pulse):
        if not isinstance(pulse, dict):
            return None
        def _strip(t):
            if not isinstance(t, dict):
                return None
            return {
                "symbol": t.get("symbol"),
                "source": t.get("source"),
                "change_pct": t.get("priceChangePercent"),
                "last": t.get("lastPrice"),
            }
        return {
            "crypto_sentiment": pulse.get("crypto_sentiment"),
            "stock_sentiment": pulse.get("stock_sentiment"),
            "total_assets_scanned": pulse.get("total_assets_scanned"),
            "top_gainers": [x for x in (_strip(t) for t in (pulse.get("top_gainers") or [])[:5]) if x],
            "top_losers": [x for x in (_strip(t) for t in (pulse.get("top_losers") or [])[:5]) if x],
        }

    def _update_momentum_analytics(self, target_symbol=None, target_kind="crypto", target_mom=0.0):
        now = time.time()
        analytics = {}

        if self.market_pulse and now - self.analytics_last_ts.get("market_pulse", 0) >= self.market_pulse_interval:
            try:
                pulse = self.market_pulse.analyze_market()
                self.analytics_cache["market_pulse"] = self._summarize_market_pulse(pulse)
                self.analytics_last_ts["market_pulse"] = now
            except Exception:
                self.analytics_cache["market_pulse"] = None
        analytics["market_pulse"] = self.analytics_cache.get("market_pulse")

        if self.lattice and now - self.analytics_last_ts.get("lattice", 0) >= self.lattice_interval:
            try:
                opportunities = self._build_lattice_opportunities()
                if opportunities:
                    state = self.lattice.update(opportunities)
                else:
                    state = self.lattice.get_state()
                summary = {
                    "phase": getattr(state, "phase", None),
                    "frequency": getattr(state, "frequency", None),
                    "risk_mod": getattr(state, "risk_mod", None),
                    "field_purity": getattr(state, "field_purity", None),
                    "carrier_strength": getattr(state, "carrier_strength", None),
                    "emergent_432": getattr(state, "emergent_432", None),
                    "schumann_alignment": getattr(state, "schumann_alignment", None),
                }
                self.analytics_cache["lattice"] = summary
                self.analytics_last_ts["lattice"] = now
            except Exception:
                self.analytics_cache["lattice"] = None
        analytics["lattice"] = self.analytics_cache.get("lattice")

        if self.luck_mapper and now - self.analytics_last_ts.get("luck", 0) >= self.luck_field_interval:
            try:
                base = self._normalize_base(target_symbol or "")
                symbol = self._normalize_symbol(target_symbol or base)
                kind = self._symbol_kind(symbol)
                price = self._get_latest_price(symbol, kind)
                history = self.market_radar.get_price_history(base, limit=120) if self.market_radar and base else []
                prices = [h["price"] for h in history] if history else []
                volatility = self._compute_volatility(prices)
                reading = self.luck_mapper.read_field(
                    price=price,
                    prices=prices if prices else None,
                    volatility=volatility,
                    trade_count=self.trades,
                )
                self.analytics_cache["luck"] = reading.to_dict() if hasattr(reading, "to_dict") else {}
                self.analytics_last_ts["luck"] = now
            except Exception:
                self.analytics_cache["luck"] = None
        analytics["luck"] = self.analytics_cache.get("luck")

        if self.whale_sonar and now - self.analytics_last_ts.get("whale_sonar", 0) >= self.whale_sonar_interval:
            try:
                snapshot = self.whale_sonar.snapshot(top=5)
                self.analytics_cache["whale_sonar"] = snapshot
                self.analytics_last_ts["whale_sonar"] = now
            except Exception:
                self.analytics_cache["whale_sonar"] = None
        analytics["whale_sonar"] = self.analytics_cache.get("whale_sonar")

        analytics["target"] = {
            "symbol": target_symbol,
            "momentum": target_mom,
        }
        self.last_momentum_analytics = analytics
        return analytics

    def _analytics_boost(self, analytics):
        if not analytics:
            return 0.0
        boost = 0.0
        luck = analytics.get("luck") or {}
        try:
            luck_score = float(luck.get("luck_field", 0) or 0)
            boost += (luck_score - 0.5) * 0.2
            if luck.get("coherence_lock"):
                boost += 0.05
        except Exception:
            pass
        lattice = analytics.get("lattice") or {}
        try:
            risk_mod = float(lattice.get("risk_mod", 1.0) or 1.0)
            boost += (risk_mod - 1.0) * 0.05
        except Exception:
            pass
        pulse = analytics.get("market_pulse") or {}
        try:
            avg_change = float((pulse.get("crypto_sentiment") or {}).get("avg_change_24h", 0) or 0)
            boost += max(-0.05, min(0.05, avg_change / 100.0))
        except Exception:
            pass
        sonar = analytics.get("whale_sonar") or {}
        try:
            overall = float(sonar.get("overall_score", 0.5) or 0.5)
            boost += (overall - 0.5) * 0.1
        except Exception:
            pass
        return boost

    def _start_analytics_loop(self):
        if self._analytics_thread and self._analytics_thread.is_alive():
            return
        self._analytics_stop.clear()
        def _run():
            while not self._analytics_stop.is_set():
                try:
                    target_symbol, target_mom, target_kind = self.coordinator.get_target()
                    self._update_momentum_analytics(target_symbol, target_kind, target_mom)
                except Exception:
                    pass
                time.sleep(self.analytics_loop_interval)
        self._analytics_thread = threading.Thread(target=_run, daemon=True)
        self._analytics_thread.start()

    def _simulate_momentum_validation(self, base):
        if not self.market_radar or not base:
            return None
        now = time.time()
        cached = self.sim_validation.get(base)
        if cached and now - cached.get("ts", 0) < self.sim_validation_ttl:
            return cached
        history = []
        if self.sse_client:
            symbol_candidates = [
                self._normalize_symbol(base),
                f"{base}/USD",
                f"{base}/USDT",
                f"{base}/USDC",
                f"{base}/BTC",
            ]
            for sym in symbol_candidates:
                stream_hist = self.sse_client.price_history.get(sym)
                if stream_hist:
                    history = list(stream_hist)
                    break
        if not history:
            history = self.market_radar.get_price_history(base, limit=2000, window_sec=self.sim_lookback_sec)
        if len(history) < 3:
            return None
        def _to_ts(val):
            try:
                ts = float(val or 0)
            except Exception:
                return 0.0
            if ts > 1e12:
                ts = ts / 1e9
            return ts

        history = sorted(history, key=lambda h: h.get("ts", h.get("time", 0)))
        times = [_to_ts(h.get("ts", h.get("time", 0))) for h in history]
        prices = [h.get("price", 0) for h in history]
        valid_pairs = []
        j = 0
        for i in range(len(times) - 1):
            start_ts = times[i]
            while j < len(times) and times[j] < start_ts + self.sim_window_sec:
                j += 1
            if j < len(times):
                valid_pairs.append((i, j))
        if not valid_pairs:
            return None
        samples = min(self.sim_count, len(valid_pairs))
        wins = 0
        for _ in range(samples):
            i, j = random.choice(valid_pairs)
            p0 = prices[i] or 0
            p1 = prices[j] or 0
            if p0 > 0 and p1 > p0:
                wins += 1
        win_rate = wins / max(1, samples)
        score = self.sim_scoreboard.get(base, {"wins": 0, "losses": 0, "streak": 0})
        if win_rate > 0.5:
            score["wins"] += 1
            score["streak"] = int(score.get("streak", 0)) + 1
        else:
            score["losses"] += 1
            score["streak"] = 0
        score["last_win_rate"] = win_rate
        score["ts"] = now
        self.sim_scoreboard[base] = score
        result = {
            "ts": now,
            "win_rate": win_rate,
            "wins": wins,
            "samples": samples,
            "window_sec": self.sim_window_sec,
            "lookback_sec": self.sim_lookback_sec,
            "streak": score.get("streak", 0),
        }
        self.sim_validation[base] = result
        return result

    def _scoreboard_ready(self, symbol):
        base = self._normalize_base(symbol)
        score = self.sim_scoreboard.get(base)
        if not score:
            if self.sim_required_wins <= 0:
                return True, 0
            return False, 0
        return int(score.get("streak", 0)) >= self.sim_required_wins, int(score.get("streak", 0))

    def _probability_score(self, symbol, momentum_score, pnl_history):
        scores = {}
        details = {}
        current_pnl = pnl_history[-1][1] if pnl_history else 0.0
        target_pnl = self.window_target_pct
        base = self._normalize_base(symbol)
        live_window = None
        live_confirmations = 0
        live_required = int(os.getenv("HIVE_PROB_LIVE_CONFIRM_REQ", "2"))
        if self.market_radar and base:
            lookback_sec = self.prob_live_window_sec
            projection_sec = self.prob_projection_sec
            live_window = self.market_radar.get_live_window_metrics(base, lookback_sec, projection_sec)
            try:
                alpaca_price = self._get_latest_price(symbol, self._symbol_kind(symbol))
            except Exception:
                alpaca_price = 0.0
            try:
                prices = self.market_radar.get_validation_prices(symbol, self._symbol_kind(symbol))
            except Exception:
                prices = {}
            tol = float(os.getenv("HIVE_PROB_LIVE_TOLERANCE_PCT", str(self.validation_tolerance_pct)))
            for src in ("binance", "kraken", "binance_ws", "kraken_ws"):
                price = float(prices.get(src, 0) or 0)
                if alpaca_price > 0 and price > 0:
                    diff = abs(alpaca_price - price) / alpaca_price * 100
                    if diff <= tol:
                        live_confirmations += 1
            details["live_validation"] = {
                "alpaca_price": alpaca_price,
                "confirmations": live_confirmations,
                "required": live_required,
                "tolerance_pct": tol,
            }
            if live_window:
                details["live_window"] = live_window

        if self.prob_use_ultimate and ultimate_predict:
            try:
                pred = ultimate_predict(
                    current_pnl=current_pnl,
                    target_pnl=target_pnl,
                    pnl_history=pnl_history or [(time.time(), current_pnl)],
                    momentum_score=momentum_score or 0.0,
                )
                scores["ultimate"] = float(pred.final_probability)
                details["ultimate"] = {
                    "final_probability": pred.final_probability,
                    "should_trade": pred.should_trade,
                    "pattern": pred.pattern_key,
                }
            except Exception:
                pass

        if self.prob_use_matrix and calculate_intelligent_probability:
            try:
                intel = calculate_intelligent_probability(
                    current_pnl=current_pnl,
                    target_pnl=target_pnl,
                    pnl_history=pnl_history or [(time.time(), current_pnl)],
                    momentum_score=momentum_score or 0.0,
                    live_delta_pct=(live_window or {}).get("delta_pct") if live_window else None,
                    live_projection_pct=(live_window or {}).get("projection_pct") if live_window else None,
                    live_samples=int((live_window or {}).get("samples") or 0),
                    live_age_sec=(live_window or {}).get("age_sec") if live_window else None,
                    live_confirmations=live_confirmations,
                    live_confirmations_required=live_required,
                )
                scores["matrix"] = float(intel.adjusted_probability)
                details["matrix"] = {
                    "adjusted_probability": intel.adjusted_probability,
                    "action": intel.action,
                    "risk_flags": intel.risk_flags,
                }
                if self.thought_bus and Thought and live_confirmations >= live_required:
                    try:
                        self.thought_bus.publish(
                            Thought(
                                source="gaia",
                                topic="probability.live_confirmed",
                                payload={
                                    "symbol": symbol,
                                    "confirmations": live_confirmations,
                                    "required": live_required,
                                    "delta_pct": (live_window or {}).get("delta_pct") if live_window else None,
                                    "projection_pct": (live_window or {}).get("projection_pct") if live_window else None,
                                },
                            )
                        )
                    except Exception:
                        pass
            except Exception:
                pass

        if self._prob_loader:
            try:
                now = time.time()
                if now - self._prob_loader_last > 60:
                    self._prob_loader.load_all_reports()
                    self._prob_loader_last = now
                base = self._normalize_base(symbol)
                report_scores = []
                for sig in self._prob_loader.signals:
                    sig_base = self._normalize_base(sig.symbol)
                    if sig_base == base:
                        report_scores.append((sig.probability + sig.confidence) / 2)
                if report_scores:
                    scores["reports"] = sum(report_scores) / len(report_scores)
                    details["reports"] = {"signals": len(report_scores)}
            except Exception:
                pass

        if self._hnc:
            try:
                base = self._normalize_base(symbol)
                signal = self._hnc.get_trading_signal(base)
                prob = float(signal.get("probability", 0) or 0)
                conf = float(signal.get("confidence", 0) or 0)
                if prob > 0:
                    scores["hnc"] = (prob + conf) / 2
                    details["hnc"] = {
                        "probability": prob,
                        "confidence": conf,
                        "action": signal.get("action"),
                    }
            except Exception:
                pass

        if not scores:
            return 0.0, scores, details

        sim = self._simulate_momentum_validation(base)
        if sim:
            scores["sim"] = float(sim.get("win_rate", 0) or 0)
            details["sim"] = {
                "win_rate": sim.get("win_rate"),
                "wins": sim.get("wins"),
                "samples": sim.get("samples"),
                "window_sec": sim.get("window_sec"),
                "lookback_sec": sim.get("lookback_sec"),
                "streak": sim.get("streak"),
            }

        avg_score = sum(scores.values()) / len(scores)
        analytics = self.last_momentum_analytics or {}
        boost = self._analytics_boost(analytics)
        if boost:
            avg_score = max(0.0, min(1.0, avg_score + boost))
            details["analytics_boost"] = boost
            details["analytics"] = {
                "luck_field": (analytics.get("luck") or {}).get("luck_field"),
                "luck_state": (analytics.get("luck") or {}).get("luck_state"),
                "lattice_phase": (analytics.get("lattice") or {}).get("phase"),
                "lattice_risk_mod": (analytics.get("lattice") or {}).get("risk_mod"),
                "crypto_sentiment": (analytics.get("market_pulse") or {}).get("crypto_sentiment"),
                "whale_score": (analytics.get("whale_sonar") or {}).get("overall_score"),
            }
        return avg_score, scores, details

    def _get_barter_score(self, from_asset, to_asset):
        if not self.use_barter_score:
            return 0.5, "disabled"
        if not to_asset:
            return 0.5, "no_target"
        from_asset = (from_asset or "USD").upper()
        to_asset = to_asset.upper()
        if self.barter_cache_only and BarterNavigator:
            try:
                nav = BarterNavigator()
                if not nav.load_cache():
                    return 0.5, "cache_missing"
                path = nav.find_path(from_asset, to_asset)
                if not path:
                    return 0.3, "no_path"
                hop_score = 1.0 - (path.num_hops - 1) * 0.1
                rate_score = min(1.0, path.total_rate)
                exchange_score = 1.0 if len(path.exchanges_used) == 1 else 0.9
                combined = (hop_score + rate_score + exchange_score) / 3
                reason = f"path_{path.num_hops}hop_{list(path.exchanges_used)[0]}"
                return combined, reason
            except Exception:
                return 0.5, "cache_error"
        if get_barter_score:
            try:
                return get_barter_score(from_asset, to_asset)
            except Exception:
                return 0.5, "barter_error"
        return 0.5, "unavailable"

    def _build_ladder_suggestion(self, bases):
        if not (self.use_ladder and self.ladder):
            return None
        if not self.market_radar:
            return None

        class _GaiaLadderClient:
            def __init__(self, outer, focus_bases):
                self._outer = outer
                self._bases = [b for b in (focus_bases or []) if b]

            def get_all_balances(self):
                data = {}
                try:
                    positions = self._outer.alpaca.get_positions() or []
                except Exception:
                    positions = []
                assets = {}
                for pos in positions:
                    sym = pos.get("symbol", "")
                    qty = float(pos.get("qty", 0) or 0)
                    base = self._outer._normalize_base(sym)
                    if qty > 0 and base:
                        assets[base] = assets.get(base, 0.0) + qty
                cash = float(self._outer.last_account.get("cash", 0) or 0)
                if cash > 0:
                    assets["USD"] = cash
                data["alpaca"] = assets
                return data

            def get_all_convertible_assets(self):
                m = {}
                bases = self._bases[:]
                if not bases:
                    bases = []
                mapping = {}
                for base in bases:
                    mapping[base] = ["USD"]
                if bases:
                    mapping["USD"] = bases
                m["alpaca"] = mapping
                return m

            def convert_to_quote(self, exchange, asset, qty, quote):
                if str(asset).upper() in ("USD", "USDT", "USDC"):
                    return float(qty or 0)
                symbol = f"{asset}/USD"
                price = self._outer._get_latest_price(symbol, "crypto")
                return float(qty or 0) * price

        focus = [b for b in (bases or []) if b]
        client = _GaiaLadderClient(self, focus)
        self.ladder.client = client
        ticker_cache = {}
        for t in self.market_radar.get_free_tickers(focus):
            base = self._normalize_base(t.get("symbol", ""))
            if not base:
                continue
            ticker_cache[base] = {
                "change24h": float(t.get("priceChangePercent", 0) or 0),
                "volume": float(t.get("quoteVolume", 0) or 0),
            }
        decision = self.ladder.step(
            ticker_cache=ticker_cache,
            net_profit=self.profit,
            portfolio_equity=self.last_account.get("equity"),
            preferred_assets=focus,
        )
        if decision:
            return {
                "ts": datetime.now().isoformat(),
                "mode": decision.mode,
                "direction": decision.direction,
                "from_asset": decision.from_asset,
                "to_asset": decision.to_asset,
                "exchange": decision.exchange,
                "amount": decision.amount,
                "reason": decision.reason,
            }
        return None

    def _reality_sources(self, bases):
        if not bases or not self.market_radar:
            return {}
        by_base = {}
        symbols = []
        base_to_symbols = {}
        for base in bases:
            if not base:
                continue
            variants = [f"{base}/USD", f"{base}/USDT", f"{base}/USDC", f"{base}/BTC"]
            base_to_symbols[base] = variants
            symbols.extend(variants)
        if self.alpaca and symbols:
            try:
                quotes = self.alpaca.get_latest_crypto_quotes(symbols) or {}
            except Exception:
                quotes = {}
            for base, variants in base_to_symbols.items():
                picked = None
                for symbol in variants:
                    quote = quotes.get(symbol)
                    if not quote:
                        continue
                    bp = float(quote.get("bp", 0) or 0)
                    ap = float(quote.get("ap", 0) or 0)
                    price = 0.0
                    if bp > 0 and ap > 0:
                        price = (bp + ap) / 2.0
                    elif bp > 0:
                        price = bp
                    elif ap > 0:
                        price = ap
                    if price <= 0:
                        continue
                    picked = (symbol, quote, price)
                    break
                if not picked:
                    continue
                symbol, quote, price = picked
                try:
                    self.market_radar._record_price(base, price, "alpaca_quote")
                except Exception:
                    pass
                change = 0.0
                history = self.market_radar.get_price_history(base, limit=120)
                if len(history) >= 2:
                    first = history[0]["price"]
                    last = history[-1]["price"]
                    if first > 0:
                        change = (last - first) / first * 100.0
                if change == 0.0 and self.sse_client:
                    try:
                        mom = self.sse_client.get_momentum(symbol, periods=10)
                        if mom is not None:
                            change = float(mom)
                    except Exception:
                        pass
                by_base[base] = {
                    "symbol": symbol,
                    "price": price,
                    "change": change,
                    "volume": float(quote.get("qv", 0) or 0),
                }
        if by_base:
            return by_base
        tickers = self.market_radar.get_free_tickers(bases)
        for ticker in tickers:
            base = self._normalize_base(ticker.get("symbol", ""))
            if not base:
                continue
            by_base[base] = {
                "price": float(ticker.get("lastPrice", 0) or 0),
                "change": float(ticker.get("priceChangePercent", 0) or 0),
                "volume": float(ticker.get("quoteVolume", 0) or 0),
            }
        return by_base

    def _build_reality_timelines(self, bases):
        bases = [self._normalize_base(b) for b in (bases or []) if b]
        bases = list(dict.fromkeys([b for b in bases if b]))
        if not bases or not self.market_radar:
            self.last_reality = None
            return None

        if self.alpaca:
            try:
                pairs = self.alpaca.get_available_pairs()
                expanded = []
                for pair in pairs or []:
                    base = pair.get("base")
                    quote = (pair.get("quote") or "").upper()
                    if base and quote in ("USD", "USDT", "USDC", "BTC"):
                        expanded.append(base)
                if expanded:
                    bases = list(dict.fromkeys(expanded))
            except Exception:
                pass

        if self.reality_base_limit > 0:
            bases = bases[: self.reality_base_limit]

        consensus = self.market_radar.last_consensus or {}
        if not consensus:
            try:
                consensus, _, _ = self.market_radar.get_crypto_consensus(bases)
            except Exception:
                consensus = {}

        tickers = self._reality_sources(bases)
        realities = {"ts": datetime.now().isoformat(), "bases": {}, "winner": None}
        winner = None
        winner_priority = None
        reject_counts = {}
        lion_data = self._get_lion_scores(bases)
        lion_scores = lion_data.get("scores") if isinstance(lion_data, dict) else {}

        branch_count = max(1, self.reality_branches)
        batch_size = self.batch_size
        if batch_size <= 0 and self.batch_count > 0:
            batch_size = max(1, math.ceil(len(bases) / self.batch_count))
        if batch_size <= 0:
            batch_size = len(bases)

        batches = [bases[i : i + batch_size] for i in range(0, len(bases), batch_size)]
        realities["batches"] = []
        all_candidates = []

        for idx, batch in enumerate(batches):
            batch_candidates = []
            for base in batch:
                data = tickers.get(base)
                if not data:
                    reject_counts["no_ticker"] = reject_counts.get("no_ticker", 0) + 1
                    continue
                price = float(data.get("price", 0) or 0)
                change = float(data.get("change", 0) or 0)
                if change < self.reality_min_change:
                    consensus_entry = consensus.get(base) if consensus else None
                    if consensus_entry:
                        try:
                            consensus_change = float(consensus_entry.get("avg", 0) or 0)
                        except Exception:
                            consensus_change = 0.0
                        if consensus_change >= self.reality_min_change:
                            change = consensus_change
                if price <= 0:
                    reject_counts["low_change"] = reject_counts.get("low_change", 0) + 1
                    continue

                source_count = int(consensus.get(base, {}).get("sources", 0) or 0)
                if not consensus:
                    source_count = max(source_count, self.reality_min_valid)
                if source_count < self.reality_min_valid:
                    reject_counts["low_sources"] = reject_counts.get("low_sources", 0) + 1
                    continue

                symbol = data.get("symbol") or f"{base}/USD"
                pnl_history = self.pnl_history.get(symbol, [])
                prob_score, prob_sources, _ = self._probability_score(symbol, change, pnl_history)
                barter_score, barter_reason = self._get_barter_score("USD", base)

                lion_score = None
                if isinstance(lion_scores, dict):
                    lion_score = lion_scores.get(base)
                subsystem = self._compute_subsystem_scores(
                    base, symbol, price, change, data.get("volume"), prob_score, lion_score=lion_score
                )
                subsystem_score = subsystem.get("score")
                if change < self.reality_min_change:
                    if subsystem_score is None or float(subsystem_score or 0) < self.reality_min_change_subsystem:
                        reject_counts["low_change"] = reject_counts.get("low_change", 0) + 1
                        continue
                confidence_base = min(
                    1.0,
                    max(0.0, (prob_score * 0.7) + (barter_score * 0.3) + (abs(change) / 100.0)),
                )
                if subsystem_score is not None:
                    confidence_base = min(
                        1.0,
                        max(
                            0.0,
                            (confidence_base * (1.0 - self._subsystem_weight))
                            + (float(subsystem_score) * self._subsystem_weight),
                        ),
                    )
                if lion_score is not None:
                    try:
                        lion_val = float(lion_score)
                    except Exception:
                        lion_val = None
                    if lion_val is not None:
                        confidence_base = min(
                            1.0,
                            max(
                                0.0,
                                (confidence_base * (1.0 - self._lion_weight))
                                + (lion_val * self._lion_weight),
                            ),
                        )

                branches = []
                for bidx in range(branch_count):
                    bias = 0.0
                    if branch_count > 1:
                        bias = (bidx / (branch_count - 1)) * 2 - 1
                    eta_base = max(1.0, self.window_seconds * (1.2 - min(abs(change) / 10.0, 0.8)))
                    eta = max(1.0, eta_base * (1.0 + (bias * 0.2)))
                    eta = max(1.0, eta / max(0.5, 0.7 + 0.3 * barter_score))
                    expected = change * (0.6 + 0.4 * (1 - abs(bias)))
                    confidence = confidence_base
                    branches.append(
                        {
                            "eta_sec": eta,
                            "expected_pct": expected,
                            "confidence": confidence,
                        }
                    )

                branches_sorted = sorted(branches, key=lambda b: (b["eta_sec"], -b["confidence"]))
                top_branches = branches_sorted[:3]
                best_branch = branches_sorted[0]

                realities["bases"][base] = {
                    "symbol": symbol,
                    "price": price,
                    "change": change,
                    "prob_score": prob_score,
                    "prob_sources": prob_sources,
                    "barter_score": barter_score,
                    "barter_reason": barter_reason,
                    "sources": source_count,
                    "top_branches": top_branches,
                    "subsystem_score": subsystem_score,
                    "subsystem": subsystem.get("scores"),
                    "lion_score": lion_score,
                }

                candidate = {
                    "symbol": symbol,
                    "base": base,
                    "eta_sec": best_branch["eta_sec"],
                    "expected_pct": best_branch["expected_pct"],
                    "confidence": best_branch["confidence"],
                    "change": change,
                    "prob_score": prob_score,
                    "barter_score": barter_score,
                    "barter_reason": barter_reason,
                    "subsystem_score": subsystem_score,
                    "subsystem": subsystem.get("scores"),
                    "lion_score": lion_score,
                }
                if self._subsystem_debug and isinstance(subsystem, dict):
                    scores = subsystem.get("scores") or {}
                    h_score = float(scores.get("harmonic") or 0)
                    c_score = float(scores.get("coherence") or 0)
                    p_score = float(scores.get("probability") or 0)
                    m_score = float(scores.get("meanrev") or 0)
                    ph_score = float(scores.get("phase") or 0)
                    l_score = float(scores.get("lion") or 0)
                    self.log(
                        "[SUBSYSTEM] "
                        + f"{symbol} h{h_score:.2f} c{c_score:.2f} "
                        + f"p{p_score:.2f} m{m_score:.2f} "
                        + f"ph{ph_score:.2f} l{l_score:.2f} "
                        + f"sum{subsystem_score:.2f}"
                    )
                batch_candidates.append(candidate)
                all_candidates.append(candidate)
                candidate_priority = self._candidate_priority(candidate)
                if winner is None or winner_priority is None or candidate_priority < winner_priority:
                    winner = candidate
                    winner_priority = candidate_priority

            batch_candidates = sorted(batch_candidates, key=lambda c: (c["eta_sec"], -c["confidence"]))
            realities["batches"].append(
                {
                    "index": idx,
                    "winners": batch_candidates[: self.batch_winners],
                }
            )

        realities["winner"] = winner
        self.last_reality = realities
        if not winner:
            try:
                if reject_counts:
                    details = ", ".join(f"{k}={v}" for k, v in reject_counts.items())
                    self.log(f"[REALITY] no winner | rejects: {details}")
                else:
                    self.log("[REALITY] no winner | rejects: none")
            except Exception:
                pass
        return realities

    def _systems_ready(self):
        if not self.require_all_systems:
            return True, ""

        if self.require_sse:
            if not self.sse_client or not getattr(self.sse_client, "running", False):
                return False, "sse_not_running"

        if self.require_ws:
            if not self.market_radar:
                return False, "market_radar_missing"
            counts = [
                len(self.market_radar.binance_ws_data or {}),
                len(self.market_radar.coinbase_ws_data or {}),
                len(self.market_radar.kraken_ws_data or {}),
            ]
            if max(counts) < self.min_ws_symbols:
                return False, f"ws_low_symbols({max(counts)})"

        if self.prob_use_hnc and not self._hnc:
            return False, "hnc_missing"
        if self.prob_use_reports and not self._prob_loader:
            return False, "prob_reports_missing"

        return True, ""

    def _record_window_outcome(self, symbol, success, pnl_pct, elapsed):
        payload = {
            "ts": datetime.now().isoformat(),
            "event": "window_result",
            "symbol": symbol,
            "success": bool(success),
            "pnl_pct": pnl_pct,
            "elapsed_sec": elapsed,
        }
        self._write_queen_memory(payload)

    def _live_confirmations(self, symbol, kind):
        prices = {}
        try:
            prices = self.market_radar.get_validation_prices(symbol, kind) if self.market_radar else {}
        except Exception:
            prices = {}
        try:
            alpaca_price = self._get_latest_price(symbol, kind)
        except Exception:
            alpaca_price = 0.0
        confirmations = 0
        if alpaca_price > 0:
            for src in ("binance", "kraken", "binance_ws", "kraken_ws"):
                price = float(prices.get(src, 0) or 0)
                if price <= 0:
                    continue
                diff = abs(alpaca_price - price) / alpaca_price * 100
                if diff <= self.live_confirm_tolerance_pct:
                    confirmations += 1
        return confirmations, prices, alpaca_price

    def _mycelium_snapshot(self):
        if not self.mycelium:
            return {}
        snapshot = {}
        try:
            snapshot["queen_signal"] = float(self.mycelium.get_queen_signal())
        except Exception:
            pass
        try:
            snapshot["coherence"] = float(self.mycelium.get_network_coherence())
        except Exception:
            pass
        try:
            snapshot["hives"] = len(getattr(self.mycelium, "hives", []) or [])
        except Exception:
            pass
        try:
            snapshot["agents"] = int(self.mycelium.get_total_agents())
        except Exception:
            pass
        return snapshot

    def _sync_bridge_state(self, reality_summary):
        if not self.bridge or not Opportunity or not CapitalState or not BridgePosition:
            return

        coherence = 0.5
        if self.mycelium:
            try:
                coherence = float(self.mycelium.get_network_coherence())
            except Exception:
                coherence = 0.5

        opportunities = []
        if reality_summary:
            for entry in reality_summary.get("top", [])[:20]:
                base = entry.get("base")
                if not base:
                    continue
                symbol = f"{base}/USD"
                eta_sec = float(entry.get("eta_sec") or 0)
                change = float(entry.get("change") or 0)
                prob_score = float(entry.get("prob_score") or 0)
                barter_score = float(entry.get("barter_score") or 0)
                score = max(0.0, 100.0 - eta_sec) + abs(change) + prob_score * 10.0 + barter_score * 5.0
                price = self._get_latest_price(symbol, "crypto")
                anomaly_flags = ["fast_eta"] if eta_sec and eta_sec < 10 else []
                opportunities.append(
                    Opportunity(
                        symbol=symbol,
                        exchange="alpaca",
                        side="BUY",
                        score=score,
                        coherence=coherence,
                        momentum=change,
                        volume=0.0,
                        price=price,
                        probability=prob_score,
                        anomaly_flags=anomaly_flags,
                        source_system=self.bridge_owner,
                    )
                )

        if opportunities:
            try:
                self.bridge.publish_opportunities(opportunities, max_count=20)
            except Exception:
                pass

        positions = self.last_positions_summary or []
        seen = set()
        for pos in positions:
            sym = pos.get("symbol")
            if not sym:
                continue
            seen.add(sym)
            try:
                qty = float(pos.get("qty") or 0)
                entry = float(pos.get("entry") or 0)
                current = float(pos.get("current") or 0)
                value = float(pos.get("value") or 0)
                pnl_pct = float(pos.get("pnl_pct") or 0)
            except Exception:
                continue
            unrealized = value * (pnl_pct / 100.0)
            bridge_pos = BridgePosition(
                symbol=sym,
                exchange="alpaca",
                side="LONG",
                size=qty,
                entry_price=entry,
                current_price=current,
                unrealized_pnl=unrealized,
                entry_time=time.time(),
                owner=self.bridge_owner,
            )
            try:
                self.bridge.register_position(bridge_pos)
            except Exception:
                pass

        try:
            existing = self.bridge.get_positions(exchange="alpaca")
            for pos in existing:
                if pos.symbol not in seen:
                    self.bridge.unregister_position("alpaca", pos.symbol)
        except Exception:
            pass

        equity = float(self.last_account.get("equity", 0) or self.last_account.get("portfolio_value", 0) or 0)
        cash = float(self.last_account.get("cash", 0) or 0)
        buying_power = float(self.last_account.get("buying_power", 0) or cash)
        allocated = sum(p.get("value", 0) or 0 for p in positions)
        unrealized = sum(
            (p.get("value", 0) or 0) * ((p.get("pnl_pct", 0) or 0) / 100)
            for p in positions
        )
        realized = float(self.profit)
        total_fees = 0.0
        trades = int(self.trades)
        wins = sum(1 for p in positions if (p.get("pnl_pct", 0) or 0) > 0)
        win_rate = wins / max(1, trades) if trades else 0.0
        capital = CapitalState(
            total_equity=equity,
            allocated_capital=allocated,
            free_capital=buying_power,
            realized_profit=realized,
            unrealized_profit=unrealized,
            total_fees=total_fees,
            net_profit=realized - total_fees,
            trades_count=trades,
            wins_count=wins,
            win_rate=win_rate,
            exchange_breakdown={"alpaca": equity},
        )
        try:
            self.bridge.update_capital(capital)
        except Exception:
            pass
        try:
            self.last_bridge_status = self.bridge.get_status()
        except Exception:
            self.last_bridge_status = {}

        if self.thought_bus and Thought:
            try:
                self.thought_bus.publish(
                    Thought(
                        source="gaia",
                        topic="bridge.status",
                        payload={"status": self.last_bridge_status},
                    )
                )
            except Exception:
                pass

    def _log_order_result(self, side, symbol, result):
        if not result:
            self.log(f"[WARN] {side.upper()} order missing response: {symbol}")
            return
        order_id = result.get("id") or result.get("order_id") or result.get("client_order_id")
        status = result.get("status")
        filled = result.get("filled_qty") or result.get("filled_qty")
        self.log(f"[ORDER] {side.upper()} {symbol} id={order_id} status={status} filled={filled}")
        self._positions_cache_ts = 0.0
        self._account_cache_ts = 0.0
        if self.thought_bus and Thought:
            try:
                self.thought_bus.publish(
                    Thought(
                        source="gaia",
                        topic="execution.order",
                        payload={
                            "side": side,
                            "symbol": symbol,
                            "order_id": order_id,
                            "status": status,
                            "filled_qty": filled,
                        },
                    )
                )
            except Exception:
                pass
        self._write_queen_memory(
            {
                "ts": datetime.now().isoformat(),
                "event": "order_ack",
                "side": side,
                "symbol": symbol,
                "order_id": order_id,
                "status": status,
                "filled_qty": filled,
            }
        )

    def _sync_recent_orders(self):
        now = time.time()
        if now - self.last_orders_ts < self.order_sync_interval:
            return
        self.last_orders_ts = now
        try:
            orders = self.alpaca.get_all_orders(status="closed", limit=20) or []
        except Exception:
            orders = []
        slim = []
        for order in orders:
            slim.append(
                {
                    "id": order.get("id"),
                    "symbol": order.get("symbol"),
                    "side": order.get("side"),
                    "status": order.get("status"),
                    "filled_qty": order.get("filled_qty") or order.get("qty"),
                    "filled_avg_price": order.get("filled_avg_price"),
                    "submitted_at": order.get("submitted_at"),
                    "filled_at": order.get("filled_at"),
                }
            )
        self.last_orders = slim

    def _sync_activity_fees(self):
        now = time.time()
        if now - self.activity_fee_last < self.activity_fee_interval:
            return
        self.activity_fee_last = now
        total_fee = 0.0
        total_notional = 0.0
        count = 0
        try:
            activities = self.alpaca.get_activities(activity_types=["FILL"], direction="desc", limit=200) or []
        except Exception:
            activities = []
        for act in activities:
            try:
                sym = (act.get("symbol") or "").upper()
                price = float(act.get("price") or act.get("fill_price") or 0)
                qty = float(act.get("qty") or act.get("filled_qty") or act.get("cum_qty") or 0)
                fee_val = act.get("commission")
                if fee_val is None:
                    fee_val = act.get("fee")
                if fee_val is None:
                    fee_val = act.get("fees")
                fee = float(fee_val or 0)
            except Exception:
                continue
            is_crypto = "/" in sym or (sym.endswith("USD") and len(sym) > 5)
            if not is_crypto:
                continue
            if price > 0 and qty > 0:
                total_notional += price * qty
                total_fee += fee
                count += 1
        fee_pct = (total_fee / total_notional * 100) if total_notional > 0 else 0.0
        self.activity_fee_pct = fee_pct
        self.last_activity_summary = {
            "count": count,
            "total_fee": total_fee,
            "notional": total_notional,
            "fee_pct": fee_pct,
        }

    def _init_log(self):
        if os.path.exists(self.log_path):
            return
        with self.log_lock:
            with open(self.log_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'event', 'exchange', 'asset', 'value',
                    'pnl_pct', 'profit_usd', 'target_symbol', 'target_mom',
                    'trades', 'profit'
                ])

    def _log_event(self, event, exchange='', asset='', value=None, pnl_pct=None, profit_usd=None):
        ts = datetime.now().isoformat()
        target_symbol, target_mom, target_kind = self.coordinator.get_target()
        with self.state_lock:
            trades = self.trades
            profit = self.profit
        with self.log_lock:
            with open(self.log_path, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    ts, event, exchange, asset, value, pnl_pct, profit_usd,
                    target_symbol, target_mom, trades, profit
                ])

    def _log_snapshot(self):
        ts = datetime.now().isoformat()
        target_symbol, target_mom, target_kind = self.coordinator.get_target()
        with self.state_lock:
            trades = self.trades
            profit = self.profit
        with self.log_lock:
            with open(self.log_path, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    ts, 'snapshot', '', '', '', '', '',
                    target_symbol, target_mom, trades, profit
                ])

    def _can_open_new_position(self):
        if not self.require_clear_profit_exit:
            return True
        try:
            positions = self.alpaca.get_positions()
        except Exception:
            return False
        active = 0
        for pos in positions:
            qty = float(pos.get("qty", 0) or 0)
            if qty > 0:
                active += 1
        if active >= self.max_positions_total:
            return False
        if active > 0:
            return False
        return True

    # ═══════════════════════════════════════════════════════════════
    # BINANCE - FAST EXECUTION
    # ═══════════════════════════════════════════════════════════════
    
    def binance_scan_and_trade(self):
        """Scan Binance positions - take any profit - deploy all cash"""
        if not self.binance:
            return
        try:
            target_symbol, target_mom, target_kind = self.coordinator.get_target()
            # Check what we hold
            for asset in ['SOL', 'BTC', 'ETH', 'AVAX', 'DOGE', 'XRP']:
                bal = self.binance.get_free_balance(asset)
                if bal < 0.00001:
                    continue
                
                pair = f'{asset}USDC'
                t = self.binance.get_ticker_price(pair)
                if not t:
                    continue
                    
                price = float(t.get('price', 0))
                value = bal * price
                
                if value < 1:
                    continue
                
                # Get entry - if none, set it NOW
                key = f'bin_{asset}'
                if self._get_entry(key) is None:
                    self._set_entry(key, price)
                    self.log(f"[ENTRY] BINANCE {asset}: Entry set @ ${price:.4f}")
                    continue
                
                entry = self._get_entry(key)

                pnl_pct = (price - entry) / entry * 100

                pos_symbol = self._normalize_symbol(asset)
                is_target = target_symbol and pos_symbol == self._normalize_symbol(target_symbol)
                if is_target:
                    should_sell = pnl_pct > 0.0
                else:
                    should_sell = pnl_pct >= 0.0

                # ANY POSITIVE = SELL (break-even floor for non-target)
                if should_sell:
                    ok, new_pnl = self._validate_sell_price(pos_symbol, entry, is_target, self._symbol_kind(pos_symbol))
                    if not ok:
                        continue
                    pnl_pct = new_pnl
                    self.log(f"[SELL] BINANCE SELL {asset}: ${value:.2f} ({pnl_pct:+.2f}%)")
                    
                    result = self.binance.place_market_order(pair, 'SELL', quantity=bal * 0.999)
                    
                    if result and ('orderId' in result or result.get('status') == 'FILLED'):
                        profit_usd = value * (pnl_pct / 100)
                        self._add_trade_profit(profit_usd)
                        self._log_event('sell', 'binance', asset, value, pnl_pct, profit_usd)
                        self.log(f"   [OK] SOLD! +${profit_usd:.4f}")
                        
                        # Remove entry so we reset on next buy
                        self._del_entry(key)
                        
                        time.sleep(0.3)
                        
                        # Immediately buy next best
                        self._binance_buy_target()
                    else:
                        self.log(f"   [WARN] Sell failed: {result}")
                        
            # Deploy any idle USDC
            usdc = self.binance.get_free_balance('USDC')
            if usdc > 2:
                self._binance_buy_target()
                
        except Exception as e:
            self.log(f"[WARN] Binance error: {e}")
    
    def _binance_buy_target(self):
        """Buy the target asset on Binance"""
        usdc = self.binance.get_free_balance('USDC')
        if usdc < 2:
            return
            
        target_symbol, target_mom, target_kind = self.coordinator.get_target()
        if target_symbol:
            pair = f"{target_symbol}USDC"
            self.log(f"[BUY] BINANCE BUY {target_symbol}: ${usdc:.2f} ({target_mom:+.1f}%)")
            
            result = self.binance.place_market_order(pair, 'BUY', quote_qty=usdc * 0.98)
            
            if result and ('orderId' in result or result.get('status') == 'FILLED'):
                # Record entry price
                t = self.binance.get_ticker_price(pair)
                price = float(t.get('price', 0))
                self._set_entry(f'bin_{target_symbol}', price)
                self._log_event('buy', 'binance', target_symbol, usdc, '', '')
                self.log(f"   OK. BOUGHT @ ${price:.4f}")
            else:
                self.log(f"   WARN: Buy failed: {result}")
            return

        if not target_symbol:
            return

        # Find best momentum
        pairs = ['SOLUSDC', 'BTCUSDC', 'ETHUSDC', 'AVAXUSDC', 'DOGEUSDC']
        best_pair, best_mom = None, -999
        
        for pair in pairs:
            try:
                t = self.binance.get_24h_ticker(pair)
                mom = float(t.get('priceChangePercent', 0))
                if mom > best_mom:
                    best_pair, best_mom = pair, mom
            except:
                pass
        
        if best_pair:
            asset = best_pair.replace('USDC', '')
            self.log(f"[BUY] BINANCE BUY {asset}: ${usdc:.2f} ({best_mom:+.1f}%)")
            
            result = self.binance.place_market_order(best_pair, 'BUY', quote_qty=usdc * 0.98)
            
            if result and ('orderId' in result or result.get('status') == 'FILLED'):
                # Record entry price
                t = self.binance.get_ticker_price(best_pair)
                price = float(t.get('price', 0))
                self._set_entry(f'bin_{asset}', price)
                self.log(f"   [OK] BOUGHT @ ${price:.4f}")
            else:
                self.log(f"   [WARN] Buy failed: {result}")

    # ═══════════════════════════════════════════════════════════════
    # ALPACA - FAST EXECUTION
    # ═══════════════════════════════════════════════════════════════
    
    def alpaca_scan_and_trade(self):
        """Scan Alpaca - take profits - deploy cash"""
        try:
            target_symbol, target_mom, target_kind = self.coordinator.get_target()
            with ThreadPoolExecutor(max_workers=3) as ex:
                f_positions = ex.submit(self._get_positions_cached)
                f_account = ex.submit(self._get_account_cached)
                f_orders = ex.submit(self._sync_recent_orders)
                positions = f_positions.result()
                acc = f_account.result()
            try:
                cash_val = float(acc.get("cash", 0) or 0)
                self.last_account = {
                    "cash": cash_val,
                    "equity": float(acc.get("equity", 0) or 0),
                    "buying_power": float(acc.get("buying_power", 0) or 0),
                    "portfolio_value": float(acc.get("portfolio_value", 0) or 0),
                }
                balances = {}
                if cash_val > 0:
                    balances["USD"] = cash_val
                for pos in positions:
                    qty = float(pos.get("qty_available", pos.get("qty", 0)) or 0)
                    if qty <= 0:
                        continue
                    norm = self._normalize_symbol(pos.get("symbol", "") or "")
                    base = norm.split("/")[0] if "/" in norm else norm
                    if base:
                        balances[base] = qty
                self.last_account["balances"] = balances
            except Exception:
                pass
            try:
                crypto_syms = []
                for pos in positions:
                    sym = self._normalize_symbol(pos.get("symbol", "") or "")
                    if "/" in sym:
                        crypto_syms.append(sym)
                self._prime_crypto_quote_cache(list(set(crypto_syms)))
            except Exception:
                pass
            self._sync_activity_fees()
            positions_summary = []
            positions_count = 0

            for pos in positions:
                sym = pos.get('symbol', '')
                pos_symbol = self._normalize_symbol(sym)
                qty = float(pos.get('qty', 0))
                entry = float(pos.get('avg_entry_price', 0))
                current = float(pos.get('current_price', 0))
                value = float(pos.get('market_value', 0))

                pnl_pct = (current - entry) / entry * 100 if entry > 0 else 0
                positions_summary.append(
                    {
                        "symbol": pos_symbol,
                        "qty": qty,
                        "entry": entry,
                        "current": current,
                        "value": value,
                        "pnl_pct": pnl_pct,
                    }
                )
                if qty > 0:
                    positions_count += 1

                if value < 0.5:
                    continue

                pnl_history = self._update_pnl_history(pos_symbol, pnl_pct)
                if self._hnc:
                    try:
                        self._hnc.feed_position_data(
                            symbol=pos_symbol,
                            exchange="ALPACA",
                            entry_price=entry,
                            entry_time=time.time(),
                            quantity=qty,
                            entry_value=entry * qty,
                            current_price=current,
                            platform_timestamp=time.time(),
                            momentum=pnl_pct,
                            coherence=min(1.0, 0.5 + abs(pnl_pct) / 10.0),
                        )
                    except Exception:
                        pass
                window = self.last_buy.get(pos_symbol)
                if window:
                    elapsed = time.time() - window.get("ts", 0)
                    if elapsed <= self.window_seconds and pnl_pct >= self.window_target_pct:
                        ok, new_pnl = self._validate_sell_price(
                            pos_symbol,
                            entry,
                            True,
                            self._symbol_kind(pos_symbol),
                            skip_delay=True,
                        )
                        if ok:
                            pnl_pct = new_pnl
                            profit_usd = value * (pnl_pct / 100)
                            ok_sell, reason = self._should_sell(pnl_pct, profit_usd, pos_symbol, self._symbol_kind(pos_symbol))
                            if not ok_sell:
                                self.log(f"[HOLD] Window exit blocked ({reason}) {pos_symbol} ({pnl_pct:+.2f}%)")
                                continue
                            self.log(f"[SELL] WINDOW EXIT {pos_symbol}: ${value:.2f} ({pnl_pct:+.2f}%)")
                            tif = 'ioc' if self._symbol_kind(sym) == 'crypto' else 'day'
                            result = self.alpaca.place_order(sym, qty, 'sell', 'market', tif)
                            if result and result.get('status') in ['filled', 'accepted', 'new']:
                                self._log_order_result("sell", pos_symbol, result)
                                self._add_trade_profit(profit_usd)
                                self._log_event('sell', 'alpaca', pos_symbol, value, pnl_pct, profit_usd)
                                self._record_window_outcome(pos_symbol, True, pnl_pct, elapsed)
                                if self._hnc:
                                    try:
                                        self._hnc.feed_position_close(
                                            symbol=pos_symbol,
                                            exit_price=current,
                                            realized_pnl=profit_usd,
                                            exit_reason="window_exit",
                                            hold_duration_mins=elapsed / 60.0,
                                            max_hold_minutes=self.window_seconds / 60.0,
                                        )
                                    except Exception:
                                        pass
                                self.log(f"   [OK] SOLD! +${profit_usd:.4f}")
                                if self.stop_on_first_profit and profit_usd >= 0.01:
                                    self._halt_after_profit = True
                                self.last_buy.pop(pos_symbol, None)
                                time.sleep(0.2)
                                self._alpaca_buy_target()
                            continue
                    elif elapsed > self.window_seconds and not window.get("recorded"):
                        window["recorded"] = True
                        self._record_window_outcome(pos_symbol, False, pnl_pct, elapsed)

                profit_usd = value * (pnl_pct / 100)
                if pnl_pct >= self.window_target_pct and pnl_pct > 0:
                    self.log(f"[FORCE SELL] TARGET HIT {pos_symbol}: ${value:.2f} ({pnl_pct:+.2f}%)")
                    tif = 'ioc' if self._symbol_kind(sym) == 'crypto' else 'day'
                    result = self.alpaca.place_order(sym, qty, 'sell', 'market', tif)
                    if result and result.get('status') in ['filled', 'accepted', 'new']:
                        self._log_order_result("sell", pos_symbol, result)
                        self._add_trade_profit(profit_usd)
                        self._log_event('sell', 'alpaca', pos_symbol, value, pnl_pct, profit_usd)
                        if self._hnc:
                            try:
                                self._hnc.feed_position_close(
                                    symbol=pos_symbol,
                                    exit_price=current,
                                    realized_pnl=profit_usd,
                                    exit_reason="target_force_exit",
                                )
                            except Exception:
                                pass
                        self.log(f"   [OK] SOLD! +${profit_usd:.4f}")
                        if self.stop_on_first_profit and profit_usd >= 0.01:
                            self._halt_after_profit = True
                        time.sleep(0.2)
                        self._alpaca_buy_target()
                    else:
                        self.log(f"   [WARN] Sell failed: {result}")
                    continue

                cash = float(self.last_account.get("cash", 0) or 0)
                cash_short = cash < self.min_trade_usd
                reality_target = None
                if self.last_reality and self.last_reality.get("winner"):
                    reality_target = self.last_reality["winner"].get("symbol")
                if reality_target:
                    target_symbol = reality_target
                is_target = target_symbol and pos_symbol == self._normalize_symbol(target_symbol)
                should_sell = pnl_pct > 0.0 if is_target else pnl_pct >= 0.0
                forced_break_even = cash_short and pnl_pct >= 0.0

                # ANY POSITIVE = SELL (break-even floor for non-target)
                if should_sell:
                    profit_usd = value * (pnl_pct / 100)
                    if not forced_break_even:
                        ok_sell, reason = self._should_sell(pnl_pct, profit_usd, pos_symbol, self._symbol_kind(pos_symbol))
                        if not ok_sell:
                            self.log(f"[HOLD] Sell blocked ({reason}) {pos_symbol} ({pnl_pct:+.2f}%)")
                            continue
                    else:
                        self.log(f"[CASH RECOVERY] Break-even exit armed {pos_symbol} (cash ${cash:.2f})")
                    ok, new_pnl = self._validate_sell_price(pos_symbol, entry, is_target, self._symbol_kind(pos_symbol))
                    if not ok:
                        self.log(f"[HOLD] Sell validation failed {pos_symbol} ({pnl_pct:+.2f}%)")
                        continue
                    pnl_pct = new_pnl
                    profit_usd = value * (pnl_pct / 100)
                    if forced_break_even and pnl_pct < 0:
                        self.log(f"[HOLD] Break-even exit invalidated {pos_symbol} ({pnl_pct:+.2f}%)")
                        continue
                    if not forced_break_even:
                        ok_sell, reason = self._should_sell(pnl_pct, profit_usd, pos_symbol, self._symbol_kind(pos_symbol))
                        if not ok_sell:
                            self.log(f"[HOLD] Sell blocked ({reason}) {pos_symbol} ({pnl_pct:+.2f}%)")
                            continue
                    target_pct, _ = self._estimate_exit_threshold(pos_symbol, self._symbol_kind(pos_symbol))
                    target_pct = max(self.window_target_pct, target_pct)
                    eta = self._estimate_eta_from_pnl(pos_symbol, pnl_pct, target_pct)
                    eta_str = f"{eta:.1f}s" if eta is not None else "n/a"
                    self.log(
                        f"[KILL READY] {pos_symbol} pnl {pnl_pct:+.2f}% target {target_pct:.2f}% eta {eta_str}"
                    )
                    self.log(f"[SELL] ALPACA SELL {pos_symbol}: ${value:.2f} ({pnl_pct:+.2f}%)")

                    tif = 'ioc' if self._symbol_kind(sym) == 'crypto' else 'day'
                    result = self.alpaca.place_order(sym, qty, 'sell', 'market', tif)

                    if result and result.get('status') in ['filled', 'accepted', 'new']:
                        self._log_order_result("sell", pos_symbol, result)
                        self._add_trade_profit(profit_usd)
                        self._log_event('sell', 'alpaca', pos_symbol, value, pnl_pct, profit_usd)
                        if self._hnc:
                            try:
                                self._hnc.feed_position_close(
                                    symbol=pos_symbol,
                                    exit_price=current,
                                    realized_pnl=profit_usd,
                                    exit_reason="take_profit",
                                )
                            except Exception:
                                pass
                        order_id = result.get("id") if isinstance(result, dict) else None
                        self.log(
                            f"[SELL EXECUTED] {pos_symbol} pnl {pnl_pct:+.2f}% profit ${profit_usd:.4f} order {order_id}"
                        )
                        if self.stop_on_first_profit and profit_usd >= 0.01:
                            self._halt_after_profit = True

                        time.sleep(0.5)
                        self._alpaca_buy_target()
                    else:
                        self.log(f"   [WARN] Sell failed: {result}")

            if positions_summary:
                preview = []
                for pos in positions_summary[:3]:
                    preview.append(
                        f"{pos['symbol']} {pos['qty']:.4f} {pos['pnl_pct']:+.2f}%"
                    )
                suffix = f" +{len(positions_summary) - 3} more" if len(positions_summary) > 3 else ""
                self.log(f"[PORTFOLIO] {len(positions_summary)} open | " + ", ".join(preview) + suffix)
                for pos in positions_summary:
                    self.log(
                        f"[POSITION] {pos['symbol']} qty {pos['qty']:.4f} entry ${pos['entry']:.6f} now ${pos['current']:.6f} pnl {pos['pnl_pct']:+.2f}% value ${pos['value']:.2f}"
                    )
            else:
                self.log("[PORTFOLIO] no open positions")

            self.last_account["positions_count"] = positions_count

            today = datetime.now().date().isoformat()
            equity = float(self.last_account.get("equity", 0) or self.last_account.get("portfolio_value", 0) or 0)
            if self.daily_date != today or self.daily_start_equity is None:
                self.daily_date = today
                self.daily_start_equity = equity
                self.daily_pnl = 0.0
                self.trading_halted = False
                self.trading_halt_reason = ""
            if self.daily_start_equity is not None:
                self.daily_pnl = equity - self.daily_start_equity
                if self.max_daily_loss_usd > 0 and self.daily_pnl <= -self.max_daily_loss_usd:
                    self.trading_halted = True
                    self.trading_halt_reason = "daily_loss_limit"
            
            # Deploy cash
            if not self.last_account:
                acc = self.alpaca.get_account()
                self.last_account = {
                    "cash": float(acc.get("cash", 0) or 0),
                    "equity": float(acc.get("equity", 0) or 0),
                    "buying_power": float(acc.get("buying_power", 0) or 0),
                    "portfolio_value": float(acc.get("portfolio_value", 0) or 0),
                }
            cash = float(self.last_account.get('cash', 0) or 0)
            if cash >= self.min_trade_usd:
                if self.trading_halted:
                    self.log(f"[WARN] Buy blocked ({self.trading_halt_reason})")
                elif not self._can_open_new_position():
                    self.log("[WARN] Buy blocked (open positions must close in profit first)")
                elif self.last_account.get("positions_count", 0) >= self.max_positions_total:
                    self.log(f"[WARN] Buy blocked (positions {self.last_account.get('positions_count', 0)}/{self.max_positions_total})")
                else:
                    self._alpaca_buy_target()
            else:
                now = time.time()
                if now - self.last_cash_warn_ts > 1.0:
                    self.last_cash_warn_ts = now
                    self.log(f"[WARN] Buy skipped (cash ${cash:.2f} < min ${self.min_trade_usd:.2f})")

            self.last_positions_summary = positions_summary
                
        except Exception as e:
            self.log(f"[WARN] Alpaca error: {e}")
    
    def _alpaca_buy_target(self):
        """Buy target on Alpaca"""
        try:
            if self.trading_halted:
                self.log(f"[WARN] Buy blocked ({self.trading_halt_reason})")
                return
            if not self.last_account:
                acc = self.alpaca.get_account()
                self.last_account = {
                    "cash": float(acc.get("cash", 0) or 0),
                    "equity": float(acc.get("equity", 0) or 0),
                    "buying_power": float(acc.get("buying_power", 0) or 0),
                    "portfolio_value": float(acc.get("portfolio_value", 0) or 0),
                }
            if self.last_account.get("positions_count", 0) >= self.max_positions_total:
                self.log(f"[WARN] Buy blocked (positions {self.last_account.get('positions_count', 0)}/{self.max_positions_total})")
                return
            cash = float(self.last_account.get('cash', 0) or 0)
            if self.max_trade_usd > 0:
                trade_budget = min(cash, self.max_trade_usd)
            else:
                trade_budget = cash
            if trade_budget < self.min_trade_usd:
                self.log(
                    f"[WARN] Buy skipped (cash ${cash:.2f} < min ${self.min_trade_usd:.2f})"
                )
                self.last_buy_blocker = "cash_below_min"
                return
            
            target_symbol, target_mom, target_kind = self.coordinator.get_target()
            winner = None
            if self.last_reality and self.last_reality.get("winner"):
                winner = self.last_reality["winner"]
            force_trade = False
            if winner:
                candidate_list = []
                if self.last_reality:
                    for batch in self.last_reality.get("batches", []) or []:
                        for entry in batch.get("winners", []) or []:
                            candidate_list.append(entry)
                candidate_list = candidate_list or [winner]
                selected = None
                best_streak = -1
                best_eta = None
                leaderboard = []
                for entry in candidate_list:
                    symbol = entry.get("symbol")
                    if not symbol:
                        continue
                    eta_sec = float(entry.get("eta_sec", 0) or 0)
                    expected_pct = float(entry.get("expected_pct", 0) or 0)
                    subsystem_score = float(entry.get("subsystem_score", 0) or 0)
                    if self.fast_money_mode:
                        if eta_sec <= 0 or eta_sec > self.fast_money_eta_sec or expected_pct <= self.fast_money_expected_pct:
                            continue
                    ready, streak = self._scoreboard_ready(symbol)
                    leaderboard.append(
                        {
                            "symbol": symbol,
                            "streak": streak,
                            "eta": eta_sec,
                            "expected": expected_pct,
                            "sub": subsystem_score,
                        }
                    )
                    if ready:
                        if streak > best_streak:
                            best_streak = streak
                            best_eta = eta_sec
                            selected = entry
                        elif streak == best_streak:
                            if best_eta is None or (eta_sec > 0 and eta_sec < best_eta):
                                best_eta = eta_sec
                                selected = entry
                            elif best_eta is not None and eta_sec == best_eta:
                                if float(entry.get("subsystem_score", 0) or 0) > float(selected.get("subsystem_score", 0) or 0):
                                    selected = entry
                if leaderboard:
                    leaderboard = sorted(
                        leaderboard,
                        key=lambda e: (-e["streak"], e["eta"] if e["eta"] > 0 else 1e9, -e["sub"]),
                    )
                    top = leaderboard[:5]
                    self.log(
                        "[CANDIDATES] "
                        + ", ".join(
                            f"{c['symbol']} s{c['streak']} eta{c['eta']:.1f}s exp{c['expected']:.2f}% sub{c['sub']:.2f}"
                            for c in top
                        )
                    )
                if selected and best_streak >= self.sim_required_wins:
                    self.log(f"[SCOREBOARD] winner {selected.get('symbol')} streak {best_streak} eta {best_eta:.1f}s")
                    if self.force_execute_on_scoreboard:
                        force_trade = True
                if not selected:
                    # If no candidate meets the streak requirement, fall back to the top candidate
                    fallback = leaderboard[0] if leaderboard else None
                    if fallback:
                        selected = next((c for c in candidate_list if c.get("symbol") == fallback.get("symbol")), fallback)
                        best_streak = int(fallback.get("streak", 0))
                        self.log(f"[WARN] Scoreboard not ready; using top candidate anyway (s{best_streak})")
                    else:
                        self.log(f"[WARN] Buy skipped (scoreboard < {self.sim_required_wins} wins)")
                        self.last_buy_blocker = "scoreboard_not_ready"
                        return
                winner = selected
                min_subscore = self._subsystem_min_score
                if min_subscore > 0:
                    try:
                        current_score = float(winner.get("subsystem_score", 0) or 0)
                    except Exception:
                        current_score = 0.0
                    if current_score < min_subscore:
                        self.log(
                            f"[WARN] Buy skipped (subsystems {current_score:.2f} < {min_subscore:.2f})"
                        )
                        self.last_buy_blocker = "subsystem_score_low"
                        return
                reality_symbol = winner.get("symbol")
                if reality_symbol:
                    target_symbol = reality_symbol
                    target_kind = "crypto"
                    target_mom = winner.get("change", target_mom)
                    self.log(
                        f"[REALITY] Winner override: {target_symbol} ETA {winner.get('eta_sec', 0):.1f}s"
                    )
            else:
                if self.reality_branches > 0:
                    self.log("[WARN] Buy skipped (no reality winner)")
                    self.last_buy_blocker = "no_reality_winner"
                    return
            if target_symbol:
                alpaca_sym = self._normalize_symbol(target_symbol)
                self.log(f"[BUY] ALPACA BUY {alpaca_sym}: ${trade_budget:.2f} ({target_mom:+.1f}%)")

                if not self._can_open_new_position():
                    self.log("[WARN] Buy blocked (open positions must close in profit first)")
                    return

                ready, reason = self._systems_ready()
                if not ready:
                    self.log(f"[WARN] Buy blocked (systems not ready): {reason}")
                    return

                if target_kind == "stock":
                    buying_power = float(self.last_account.get("buying_power", 0) or 0)
                    if buying_power > trade_budget:
                        trade_budget = min(buying_power, self.max_trade_usd)

                if not force_trade:
                    ok_buy, reason = self._should_buy(target_mom or 0.0)
                    if not ok_buy:
                        self.log(f"[WARN] Buy blocked ({reason}): {alpaca_sym}")
                        self.last_buy_blocker = reason
                        return

                price = self._get_latest_price(alpaca_sym, target_kind)
                if price <= 0 and target_kind == "crypto":
                    base = self._normalize_base(alpaca_sym)
                    if base:
                        fallback = f"{base}/USD"
                        if fallback != alpaca_sym:
                            price = self._get_latest_price(fallback, target_kind)
                            if price > 0:
                                self.log(f"[INFO] Fallback to {fallback} for pricing")
                                alpaca_sym = fallback
            if price <= 0:
                self.log(f"[WARN] Buy skipped (no price): {alpaca_sym}")
                self.last_buy_blocker = "no_price"
                return

                qty = (trade_budget * 0.95) / price
                tif = 'ioc' if target_kind == 'crypto' else 'day'

                pnl_history = self.pnl_history.get(alpaca_sym, [])
                prob_score, prob_sources, prob_details = self._probability_score(
                    alpaca_sym,
                    target_mom or 0.0,
                    pnl_history,
                )
                if self.prob_gate_required:
                    if len(prob_sources) < self.prob_sources_min or prob_score < self.prob_min_score:
                        self.log(
                            f"[WARN] Buy skipped (prob {prob_score:.2f}, sources {len(prob_sources)}): {alpaca_sym}"
                        )
                        return

                if not force_trade:
                    ok, confirmations, prices = self._validate_buy_price(alpaca_sym, target_kind)
                    if not ok:
                        self.log(
                            f"[WARN] Buy skipped (validation {confirmations}/{self.buy_confirmations}): {alpaca_sym} prices={prices}"
                        )
                        return
                else:
                    self.log("[FORCE] Scoreboard winner executing buy without extra gates")

                try:
                    if target_kind == "crypto":
                        result = self.alpaca.place_market_order(
                            alpaca_sym, "buy", quote_qty=trade_budget
                        )
                    else:
                        result = self.alpaca.place_order(alpaca_sym, qty, 'buy', 'market', tif)
                    if result:
                        self._log_order_result("buy", alpaca_sym, result)
                        self._log_event('buy', 'alpaca', alpaca_sym, trade_budget, '', '')
                        self.log(f"   [OK] BOUGHT")
                        self.last_buy[alpaca_sym] = {
                            "ts": time.time(),
                            "entry": price,
                            "recorded": False,
                        }
                        self._write_queen_memory(
                            {
                                "ts": datetime.now().isoformat(),
                                "event": "probability_gate",
                                "symbol": alpaca_sym,
                                "prob_score": prob_score,
                                "prob_sources": prob_sources,
                                "prob_details": prob_details,
                            }
                        )
                    else:
                        self.log(f"   [WARN] Buy failed: {result}")
                except Exception as e:
                    self.log(f"   [WARN] Buy error: {e}")
                return
            if not target_symbol:
                self.log("[WARN] Buy skipped (no target)")
                return

            # Use Binance momentum data
            pairs = ['SOLUSDC', 'BTCUSDC', 'ETHUSDC']
            best_asset, best_mom = None, -999
            
            for pair in pairs:
                try:
                    t = self.binance.get_24h_ticker(pair)
                    mom = float(t.get('priceChangePercent', 0))
                    if mom > best_mom:
                        best_asset = pair.replace('USDC', '')
                        best_mom = mom
                except:
                    pass
            
            if best_asset:
                alpaca_sym = f'{best_asset}/USD'
                self.log(f"[BUY] ALPACA BUY {best_asset}: ${trade_budget:.2f} ({best_mom:+.1f}%)")
                
                # Get price and calc qty
                try:
                    quotes = self.alpaca.get_latest_crypto_quotes([alpaca_sym])
                    price = float(quotes[alpaca_sym].get('ap', 0))
                    qty = (trade_budget * 0.95) / price
                    
                    result = self.alpaca.place_order(alpaca_sym, qty, 'buy', 'market', 'ioc')
                    if result:
                        self.log(f"   [OK] BOUGHT")
                except Exception as e:
                    self.log(f"   [WARN] Buy error: {e}")
                    
        except Exception as e:
            self.log(f"[WARN] Alpaca buy error: {e}")

    # ═══════════════════════════════════════════════════════════════
    # KRAKEN - FAST EXECUTION
    # ═══════════════════════════════════════════════════════════════
    
    def kraken_scan_and_trade(self):
        """Scan Kraken - take profits - deploy USD"""
        if not self.kraken:
            return
        try:
            target_symbol, target_mom, target_kind = self.coordinator.get_target()
            acct = self.kraken.account()
            usd_bal = 0
            
            for bal in acct.get('balances', []):
                asset = bal.get('asset', '')
                free = float(bal.get('free', 0))
                
                if free <= 0:
                    continue
                
                # Track USD
                if asset in ['USD', 'USDC', 'ZUSD']:
                    usd_bal += free
                    continue
                
                if asset in ['USDT', 'EUR', 'ZEUR']:
                    continue
                
                # It's a crypto - check value
                pair = f'{asset}USD'
                try:
                    ticker = self.kraken.get_ticker(pair)
                    price = float(ticker.get('price', 0))
                except:
                    continue
                
                value = free * price
                if value < 1:
                    continue
                
                # Get entry
                key = f'krk_{asset}'
                if self._get_entry(key) is None:
                    self._set_entry(key, price)
                    self.log(f"[ENTRY] KRAKEN {asset}: Entry set @ ${price:.4f}")
                    continue
                
                entry = self._get_entry(key)

                pnl_pct = (price - entry) / entry * 100

                pos_symbol = self._normalize_symbol(asset)
                is_target = target_symbol and pos_symbol == self._normalize_symbol(target_symbol)
                if is_target:
                    should_sell = pnl_pct > 0.0
                else:
                    should_sell = pnl_pct >= 0.0

                # ANY POSITIVE = SELL (break-even floor for non-target)
                if should_sell:
                    self.log(f"[SELL] KRAKEN SELL {asset}: ${value:.2f} ({pnl_pct:+.2f}%)")
                    
                    result = self.kraken.place_market_order(pair, 'sell', quantity=free * 0.999)
                    
                    # Check for ANY success indicator
                    if result and (result.get('txid') or result.get('status') == 'FILLED' or 
                                   result.get('orderId') or 'dryRun' in result):
                        profit_usd = value * (pnl_pct / 100)
                        self._add_trade_profit(profit_usd)
                        self._log_event('sell', 'kraken', asset, value, pnl_pct, profit_usd)
                        self.log(f"   [OK] SOLD! +${profit_usd:.4f}")
                        
                        self._del_entry(key)
                        time.sleep(0.3)
                        self._kraken_buy_target()
                    else:
                        self.log(f"   [WARN] Sell failed: {result}")
            
            # Deploy USD
            if usd_bal > 2:
                self._kraken_buy_target()
                
        except Exception as e:
            self.log(f"[WARN] Kraken error: {e}")
    
    def _kraken_buy_target(self):
        """Buy target on Kraken"""
        try:
            acct = self.kraken.account()
            usd = sum(float(b.get('free', 0)) for b in acct.get('balances', []) 
                     if b.get('asset') in ['USD', 'USDC', 'ZUSD'])
            
            if usd < 2:
                return
            
            target_symbol, target_mom, target_kind = self.coordinator.get_target()
            if target_symbol:
                kraken_pair = f'{target_symbol}USD'
                self.log(f"[BUY] KRAKEN BUY {target_symbol}: ${usd:.2f} ({target_mom:+.1f}%)")
                
                result = self.kraken.place_market_order(kraken_pair, 'buy', quote_qty=usd * 0.95)
                
                if result and (result.get('txid') or 'dryRun' in result):
                    ticker = self.kraken.get_ticker(kraken_pair)
                    price = float(ticker.get('price', 0))
                    self._set_entry(f'krk_{target_symbol}', price)
                    self._log_event('buy', 'kraken', target_symbol, usd, '', '')
                    self.log(f"   OK. BOUGHT @ ${price:.4f}")
                else:
                    self.log(f"   WARN: Buy failed: {result}")
                return

            if not target_symbol:
                return

            # Use Binance momentum
            pairs = ['SOLUSDC', 'BTCUSDC', 'ETHUSDC']
            best_asset, best_mom = None, -999
            
            for pair in pairs:
                try:
                    t = self.binance.get_24h_ticker(pair)
                    mom = float(t.get('priceChangePercent', 0))
                    if mom > best_mom:
                        best_asset = pair.replace('USDC', '')
                        best_mom = mom
                except:
                    pass
            
            if best_asset:
                kraken_pair = f'{best_asset}USD'
                self.log(f"[BUY] KRAKEN BUY {best_asset}: ${usd:.2f} ({best_mom:+.1f}%)")
                
                result = self.kraken.place_market_order(kraken_pair, 'buy', quote_qty=usd * 0.95)
                
                if result and (result.get('txid') or 'dryRun' in result):
                    ticker = self.kraken.get_ticker(kraken_pair)
                    price = float(ticker.get('price', 0))
                    self._set_entry(f'krk_{best_asset}', price)
                    self.log(f"   [OK] BOUGHT @ ${price:.4f}")
                else:
                    self.log(f"   [WARN] Buy failed: {result}")
                    
        except Exception as e:
            self.log(f"[WARN] Kraken buy error: {e}")

    # ═══════════════════════════════════════════════════════════════
    # MAIN LOOP - PARALLEL AGGRESSIVE SCANNING
    # ═══════════════════════════════════════════════════════════════
    
    def run_cycle(self):
        """Run one aggressive cycle across all platforms"""
        self.coordinator.update_target()
        try:
            bases = []
            if self.market_radar and self.market_radar.last_focus_bases:
                bases = list(self.market_radar.last_focus_bases)
            elif self.coordinator.crypto_symbols:
                bases = [sym.split("/", 1)[0] if "/" in sym else sym.replace("USD", "") for sym in self.coordinator.crypto_symbols]
            bases = [b for b in bases if b]
            if bases:
                reality_bases = bases[: self.reality_base_limit] if self.reality_base_limit > 0 else bases
                reality = self._build_reality_timelines(reality_bases)
                winner = reality.get("winner") if isinstance(reality, dict) else None
                if winner and winner.get("symbol"):
                    self.last_reality = reality
                    with self.coordinator.lock:
                        self.coordinator.target_symbol = winner.get("symbol")
                        self.coordinator.target_kind = "crypto"
                        self.coordinator.target_momentum = float(winner.get("change") or 0.0)
                        self.coordinator.last_update = time.time()
        except Exception:
            pass
        with ThreadPoolExecutor(max_workers=1) as ex:
            ex.submit(self.alpaca_scan_and_trade)

    def _log_live_process(self, cycle):
        target_symbol, target_mom, target_kind = self.coordinator.get_target()
        focus = []
        validation = None
        if self.market_radar:
            focus = self.market_radar.last_focus_bases or []
            validation = self.market_radar.last_validation_base
        consensus = self.market_radar.last_consensus if self.market_radar else {}
        reality = None
        if self.reality_branches > 0:
            bases = focus or list((consensus or {}).keys())
            if bases:
                reality = self._build_reality_timelines(bases)
        ladder = self._build_ladder_suggestion(focus or list((consensus or {}).keys()))
        if ladder:
            self.last_ladder = ladder
        focus_str = ",".join(focus[:9]) if focus else "None"
        validation_str = validation or "None"
        target = target_symbol or "None"
        reality_note = ""
        if reality and reality.get("winner"):
            winner = reality["winner"]
            base = winner.get("base") or self._normalize_base(winner.get("symbol", ""))
            reality_note = f" | REALITY: {base} {winner.get('eta_sec', 0):.1f}s"
        self.log(f"[LIVE] CYCLE {cycle} | TARGET: {target} ({target_mom:+.1f}%) | COINBASE9: {focus_str} | ALPACA1: {validation_str}{reality_note}")
        if self.mycelium and target_symbol:
            try:
                signal = max(-1.0, min(1.0, (target_mom or 0) / 10.0))
                confidence = min(1.0, abs(target_mom or 0) / 10.0)
                self.mycelium.receive_external_signal("gaia_momentum", signal, confidence=confidence)
            except Exception:
                pass
        if self.store_live_memory:
            ws_heartbeat = {}
            if self.market_radar:
                ws_heartbeat = {
                    "binance_ws_count": len(self.market_radar.binance_ws_data or {}),
                    "coinbase_ws_count": len(self.market_radar.coinbase_ws_data or {}),
                    "kraken_ws_count": len(self.market_radar.kraken_ws_data or {}),
                    "binance_ws_last": self.market_radar.binance_ws_last,
                    "coinbase_ws_last": self.market_radar.coinbase_ws_last,
                    "kraken_ws_last": self.market_radar.kraken_ws_last,
                }
            sse_stats = {}
            if self.sse_client:
                sse_stats = dict(self.sse_client.stats)
                sse_stats["running"] = bool(getattr(self.sse_client, "running", False))
            analytics = self.last_momentum_analytics or {}
            reality_summary = None
            if reality:
                summary = []
                for base, entry in reality.get("bases", {}).items():
                    branches = entry.get("top_branches") or []
                    best_eta = branches[0]["eta_sec"] if branches else None
                    summary.append(
                        {
                            "base": base,
                            "eta_sec": best_eta,
                            "change": entry.get("change", 0),
                            "prob_score": entry.get("prob_score", 0),
                            "barter_score": entry.get("barter_score", 0),
                        }
                    )
                summary = sorted(summary, key=lambda item: (item["eta_sec"] or 9999, -item["change"]))
                reality_summary = {
                    "winner": reality.get("winner"),
                    "top": summary[:10],
                }
            self._sync_bridge_state(reality_summary)
            payload = {
                "ts": datetime.now().isoformat(),
                "cycle": cycle,
                "target_symbol": target_symbol,
                "target_momentum": target_mom,
                "logic": self._queen_logic_summary(target_symbol, target_mom, target_kind),
                "coinbase_focus": focus,
                "alpaca_validation": validation,
                "consensus": consensus,
                "reality": reality_summary,
                "positions": self.last_positions_summary,
                "portfolio": {
                    "value": sum(p.get("value", 0) or 0 for p in self.last_positions_summary),
                    "unrealized": sum(
                        (p.get("value", 0) or 0) * ((p.get("pnl_pct", 0) or 0) / 100)
                        for p in self.last_positions_summary
                    ),
                    "winners": sum(1 for p in self.last_positions_summary if (p.get("pnl_pct", 0) or 0) > 0),
                    "losers": sum(1 for p in self.last_positions_summary if (p.get("pnl_pct", 0) or 0) < 0),
                    "prime_usd": self.min_profit_usd,
                },
                "account": self.last_account,
                "ladder": self.last_ladder,
                "orders": self.last_orders,
                "activity": self.last_activity_summary,
                "bridge": self.last_bridge_status,
                "analytics": analytics,
                "compound": {
                    "level": self.compound_index,
                    "next_target": self.compound_checkpoints[self.compound_index]
                    if self.compound_checkpoints and self.compound_index < len(self.compound_checkpoints)
                    else None,
                    "checkpoints": self.compound_checkpoints,
                    "profit_total": self.profit,
                    "auto_expand": self.compound_auto_expand,
                    "multiplier": self.compound_multiplier,
                },
                "validation": self.last_validation,
                "pnl_summary": {
                    "trades": self.trades,
                    "profit": self.profit,
                    "entries": len(self.entries),
                },
                "heartbeat": ws_heartbeat,
                "sse": sse_stats,
            }
            live_snapshot = {
                "ts": payload["ts"],
                "cycle": cycle,
                "target": {"symbol": target_symbol, "momentum": target_mom, "kind": target_kind},
                "scan": {
                    "coinbase_focus": focus,
                    "alpaca_validation": validation,
                    "consensus": consensus,
                },
                "reality": reality_summary,
                "portfolio": payload.get("portfolio"),
                "account": payload.get("account"),
                "ladder": payload.get("ladder"),
                "compound": payload.get("compound"),
                "activity": payload.get("activity"),
                "validation": payload.get("validation"),
                "bridge": payload.get("bridge"),
                "orders": payload.get("orders"),
                "analytics": payload.get("analytics"),
            }
            if self.thought_bus and Thought:
                try:
                    self.thought_bus.publish(
                        Thought(
                            source="gaia",
                            topic="queen.live_state",
                            payload=live_snapshot,
                        )
                    )
                except Exception:
                    pass
            if self.mycelium and hasattr(self.mycelium, "broadcast_signal"):
                try:
                    self.mycelium.broadcast_signal("queen_live_state", live_snapshot)
                except Exception:
                    pass
            if self.dash_heartbeat_path:
                try:
                    if os.path.exists(self.dash_heartbeat_path):
                        with open(self.dash_heartbeat_path, "r", encoding="utf-8") as f:
                            dash = json.load(f)
                        dash_ts = dash.get("ts")
                        dash_epoch = dash.get("epoch")
                        age = time.time() - float(dash_epoch or 0)
                        payload["link"] = {
                            "dashboard_ts": dash_ts,
                            "dashboard_age_sec": max(0.0, age),
                        }
                except Exception:
                    payload["link"] = {"dashboard_age_sec": None}
            self._write_queen_memory(payload)

    def _write_queen_memory(self, payload):
        try:
            def _safe_default(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return str(obj)
            with open(self.memory_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=True, default=_safe_default) + "\n")
        except Exception as e:
            self.log(f"[WARN] Memory write failed: {e}")
    
    def print_status(self):
        """Quick status"""
        with self.state_lock:
            trades = self.trades
            profit = self.profit
            entries = len(self.entries)
        target_symbol, target_mom, target_kind = self.coordinator.get_target()
        if target_symbol:
            target = f"{target_symbol} ({target_mom:+.1f}%)"
        else:
            target = "None"

        wave_last = self.coordinator.wave_last_scan
        interval = self.coordinator.wave_scan_interval
        if wave_last > 0:
            eta = max(0, interval - (time.time() - wave_last))
        else:
            eta = interval

        self.log(f"=== TRADES: {trades} | PROFIT: ${profit:.4f} | ENTRIES: {entries} | TARGET: {target} | WAVE_ETA: {eta:.0f}s ===")

        try:
            cash = float(self.last_account.get("cash", 0) or 0)
            buying_power = float(self.last_account.get("buying_power", 0) or 0)
            equity = float(self.last_account.get("equity", 0) or self.last_account.get("portfolio_value", 0) or 0)
            positions_count = int(self.last_account.get("positions_count", 0) or 0)
            ob_metrics = {}
            if target_symbol and self._symbol_kind(target_symbol) == "crypto":
                ob_metrics = self._get_orderbook_metrics(self._normalize_symbol(target_symbol)) or {}
            exit_threshold, _ = self._estimate_exit_threshold(
                target_symbol or "", self._symbol_kind(target_symbol or "crypto")
            )
            gates = []
            if self.require_sell_validation:
                gates.append("sell_validation")
            if self.require_live_confirmations:
                gates.append("live_confirm")
            if self.prob_gate_required:
                gates.append("prob_gate")
            gate_str = ",".join(gates) if gates else "none"
            last_order = self.last_orders[-1] if self.last_orders else {}
            last_order_id = last_order.get("id") or last_order.get("order_id") or "n/a"
            last_order_status = last_order.get("status") or "n/a"
            self.log(
                f"[DEBUG] cash ${cash:.2f} | buying ${buying_power:.2f} | equity ${equity:.2f} | positions {positions_count} | min ${self.min_trade_usd:.2f} | gates {gate_str} | last_order {last_order_status}:{last_order_id}"
            )
            if self.last_buy_blocker:
                self.log(f"[DEBUG] buy_blocker {self.last_buy_blocker}")
            if ob_metrics:
                self.log(
                    f"[DEBUG] orderbook spread {ob_metrics.get('spread_pct', 0):.3f}% | ask_depth ${ob_metrics.get('ask_depth_usd', 0):.2f} | bid_depth ${ob_metrics.get('bid_depth_usd', 0):.2f} | exit_thr {exit_threshold:.3f}%"
                )
            if target_symbol:
                price = self._get_latest_price(target_symbol, self._symbol_kind(target_symbol))
                srcs = list((self.last_validation or {}).get("sources", []) or [])
                self.log(
                    f"[DEBUG] price ${price:.6f} | validation_sources {len(srcs)} | target {target_symbol}"
                )
        except Exception:
            pass
    
    def run(self):
        """RUN FOREVER - TAKE EVERYTHING"""
        print()
        print("AGGRESSIVE MODE: break-even floor; any positive outcome")
        print("NO GATES - Just profits")
        print("Alpaca-only scanning (wave + SSE)")
        print()

        full_market = os.getenv("HIVE_FULL_MARKET_TEST", "false").lower() == "true"
        if full_market and self.market_radar:
            try:
                snapshot = self.market_radar.build_full_market_snapshot()
                self._write_queen_memory({"full_market": snapshot})
                self.log(f"[OK] Full market snapshot stored: {snapshot.get('binance_count', 0)} symbols")
            except Exception as e:
                self.log(f"[WARN] Full market snapshot failed: {e}")

        self._start_analytics_loop()
        
        cycle = 0
        run_forever = os.getenv('HIVE_RUN_FOREVER', 'true').lower() == 'true'
        max_cycles_env = os.getenv('HIVE_MAX_CYCLES')
        max_cycles = None
        if not run_forever and max_cycles_env and max_cycles_env.isdigit():
            max_cycles = int(max_cycles_env)
        while True:
            try:
                trade_cycle = self.trade_every_cycles <= 1 or (cycle % self.trade_every_cycles == 0)
                if trade_cycle:
                    self.run_cycle()
                else:
                    self.coordinator.update_target()
                    try:
                        target_symbol, target_mom, target_kind = self.coordinator.get_target()
                        self._update_momentum_analytics(target_symbol, target_kind, target_mom)
                    except Exception:
                        pass
                if cycle % self.log_every == 0:
                    self._log_snapshot()
                if self.live_log_every > 0 and cycle % self.live_log_every == 0:
                    self._log_live_process(cycle)
                cycle += 1
                if max_cycles and cycle >= max_cycles:
                    self.print_status()
                    net = self.profit
                    if net >= 0:
                        self.log(f"[OK] NET POSITIVE: ${net:.4f}")
                    else:
                        self.log(f"[WARN] NET NEGATIVE: ${net:.4f}")
                    break
                
                if cycle % 10 == 0:
                    self.print_status()

                if self._halt_after_profit:
                    self.log("[OK] First profitable cycle complete. Stopping.")
                    self.print_status()
                    break

                time.sleep(self.cycle_sleep_sec)  # Fast cycle
                
            except KeyboardInterrupt:
                print()
                self.log("STOPPED")
                self.print_status()
                break
            except Exception as e:
                self.log(f"ERROR: {e}")
                time.sleep(2)


if __name__ == "__main__":
    r = AggressiveReclaimer()
    r.run()
