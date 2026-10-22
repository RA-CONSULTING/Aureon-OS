#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║     UNIFIED MULTI-SOURCE DATA FEED — Capital + Ollama + Binance + Alpaca    ║
║                                                                              ║
║  Fetches prices from ALL sources, normalizes, feeds into chain-link          ║
║  shadow trading system.                                                      ║
║                                                                              ║
║  SOURCES:                                                                    ║
║    • Capital.com — Forex, indices, commodities CFDs                          ║
║    • Binance — Crypto spot prices                                            ║
║    • Alpaca — US stocks (pre/post market)                                    ║
║    • Ollama Cloud — AI cognitive analysis                                    ║
║                                                                              ║
║  SECURITY: credentials are read from environment variables or a .env file;   ║
║  no secrets are stored in source code. If credentials are missing, the       ║
║  affected source is skipped with a warning.                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import time
import math
import asyncio
import aiohttp
import requests
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

RADAR_DIR = Path("C:/Users/user/.kimi_openclaw/workspace/aureon_radar")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(RADAR_DIR / "multi_source_feed.log")
    ]
)
logger = logging.getLogger('MULTI_SOURCE')

# ═══════════════════════════════════════════════════════════════════════════════
# CREDENTIALS — loaded from environment / .env; never hardcoded.
# ═══════════════════════════════════════════════════════════════════════════════

def _load_dotenv() -> None:
    """Load .env files from repo root and radar directory if python-dotenv is available."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    repo_root = Path(__file__).resolve().parents[2]
    for path in (repo_root / ".env", RADAR_DIR / ".env", Path.cwd() / ".env"):
        if path.exists():
            load_dotenv(dotenv_path=str(path), override=False)

_load_dotenv()

def _env(name: str, fallback: Optional[str] = None) -> Optional[str]:
    return os.getenv(name, fallback) or None

# Capital.com
CAPITAL_KEY = _env("CAPITAL_API_KEY")
CAPITAL_ID = _env("CAPITAL_IDENTIFIER")
CAPITAL_PASS = _env("CAPITAL_PASSWORD") or _env("CAPITAL_API_PASSWORD")

# Binance
BINANCE_KEY = _env("BINANCE_API_KEY") or _env("BINANCE_KEY")
BINANCE_SECRET = _env("BINANCE_API_SECRET") or _env("BINANCE_SECRET")

# Alpaca
ALPACA_KEY = _env("ALPACA_API_KEY_ID") or _env("ALPACA_API_KEY")
ALPACA_SECRET = _env("ALPACA_API_SECRET_KEY") or _env("ALPACA_SECRET_KEY")

# Ollama
OLLAMA_KEY = _env("OLLAMA_API_KEY")

# ═══════════════════════════════════════════════════════════════════════════════
# SYMBOL MAPPING — Cross-market symbols
# ═══════════════════════════════════════════════════════════════════════════════

CROSS_MARKET_SYMBOLS = {
    # Forex (Capital.com primary)
    "USDJPY": {"capital": "USDJPY", "binance": None, "alpaca": None, "type": "forex"},
    "EURUSD": {"capital": "EURUSD", "binance": None, "alpaca": None, "type": "forex"},
    "GBPUSD": {"capital": "GBPUSD", "binance": None, "alpaca": None, "type": "forex"},
    # Crypto (Binance primary, Capital CFD)
    "BTCUSD": {"capital": "BTCUSD", "binance": "BTCUSDT", "alpaca": "BTCUSD", "type": "crypto"},
    "ETHUSD": {"capital": "ETHUSD", "binance": "ETHUSDT", "alpaca": "ETHUSD", "type": "crypto"},
    # Commodities (Capital.com primary)
    "GOLD": {"capital": "GOLD", "binance": None, "alpaca": None, "type": "commodity"},
    "SILVER": {"capital": "SILVER", "binance": None, "alpaca": None, "type": "commodity"},
    "OIL_CRUDE": {"capital": "OIL_CRUDE", "binance": None, "alpaca": None, "type": "commodity"},
    "NATURALGAS": {"capital": "NATURALGAS", "binance": None, "alpaca": None, "type": "commodity"},
    # Indices (Capital.com primary)
    "US100": {"capital": "US100", "binance": None, "alpaca": None, "type": "index"},
    # Stocks (Alpaca primary)
    "AAPL": {"capital": None, "binance": None, "alpaca": "AAPL", "type": "stock"},
    "TSLA": {"capital": None, "binance": None, "alpaca": "TSLA", "type": "stock"},
    "NVDA": {"capital": None, "binance": None, "alpaca": "NVDA", "type": "stock"},
}

# ═══════════════════════════════════════════════════════════════════════════════
# DATA FEED CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

class CapitalFeed:
    """Capital.com CFD price feed."""

    def __init__(self):
        self.cst = None
        self.x_sec = None
        self._enabled = bool(CAPITAL_KEY and CAPITAL_ID and CAPITAL_PASS)
        if not self._enabled:
            logger.warning("Capital.com credentials not set; Capital feed disabled")
        else:
            self._auth()

    def _auth(self):
        try:
            resp = requests.post(
                "https://api-capital.backend-capital.com/api/v1/session",
                json={"identifier": CAPITAL_ID, "password": CAPITAL_PASS},
                headers={"X-CAP-API-KEY": CAPITAL_KEY, "Content-Type": "application/json"},
                timeout=10
            )
            resp.raise_for_status()
            self.cst = resp.headers.get("CST")
            self.x_sec = resp.headers.get("X-SECURITY-TOKEN")
        except Exception as e:
            logger.error(f"Capital auth: {e}")

    def get_price(self, symbol: str) -> Optional[Dict]:
        if not self._enabled:
            return None
        if not self.cst:
            self._auth()
        try:
            resp = requests.get(
                f"https://api-capital.backend-capital.com/api/v1/markets/{symbol}",
                headers={"X-CAP-API-KEY": CAPITAL_KEY, "CST": self.cst, "X-SECURITY-TOKEN": self.x_sec},
                timeout=10
            )
            if resp.status_code == 401:
                self._auth()
                return None
            resp.raise_for_status()
            data = resp.json()
            snap = data.get("snapshot", {})
            return {
                "source": "capital",
                "symbol": symbol,
                "price": snap.get("offer", 0),
                "bid": snap.get("bid", 0),
                "change_pct": snap.get("netChange", 0),
                "timestamp": time.time()
            }
        except Exception as e:
            logger.debug(f"Capital price error {symbol}: {e}")
            return None


class BinanceFeed:
    """Binance spot price feed (no auth needed for prices)."""

    def __init__(self):
        self._enabled = True

    def get_price(self, symbol: str) -> Optional[Dict]:
        try:
            resp = requests.get(
                f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}",
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "source": "binance",
                "symbol": symbol,
                "price": float(data.get("lastPrice", 0)),
                "bid": float(data.get("bidPrice", 0)),
                "change_pct": float(data.get("priceChangePercent", 0)),
                "timestamp": time.time()
            }
        except Exception as e:
            logger.debug(f"Binance price error {symbol}: {e}")
            return None


class AlpacaFeed:
    """Alpaca stock price feed."""

    def __init__(self):
        self._enabled = bool(ALPACA_KEY and ALPACA_SECRET)
        if not self._enabled:
            logger.warning("Alpaca credentials not set; Alpaca feed disabled")

    def get_price(self, symbol: str) -> Optional[Dict]:
        if not self._enabled:
            return None
        try:
            resp = requests.get(
                f"https://data.alpaca.markets/v2/stocks/{symbol}/quotes/latest",
                headers={"APCA-API-KEY-ID": ALPACA_KEY, "APCA-API-SECRET-KEY": ALPACA_SECRET},
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            quote = data.get("quote", {})
            return {
                "source": "alpaca",
                "symbol": symbol,
                "price": float(quote.get("ap", 0)),  # Ask price
                "bid": float(quote.get("bp", 0)),
                "change_pct": 0,  # Would need separate call
                "timestamp": time.time()
            }
        except Exception as e:
            logger.debug(f"Alpaca price error {symbol}: {e}")
            return None

# ═══════════════════════════════════════════════════════════════════════════════
# UNIFIED FEED
# ═══════════════════════════════════════════════════════════════════════════════

class UnifiedMultiSourceFeed:
    """
    Aggregates prices from ALL sources.
    Cross-validates prices across exchanges.
    """

    def __init__(self):
        self.capital = CapitalFeed()
        self.binance = BinanceFeed()
        self.alpaca = AlpacaFeed()

    def fetch_all(self) -> Dict[str, Dict]:
        """Fetch prices for ALL symbols from ALL sources."""
        results = {}

        for unified_symbol, mapping in CROSS_MARKET_SYMBOLS.items():
            sources = []

            # Try Capital.com
            if mapping["capital"] and self.capital._enabled:
                data = self.capital.get_price(mapping["capital"])
                if data:
                    sources.append(data)

            # Try Binance
            if mapping["binance"]:
                data = self.binance.get_price(mapping["binance"])
                if data:
                    data["unified_symbol"] = unified_symbol
                    sources.append(data)

            # Try Alpaca
            if mapping["alpaca"] and self.alpaca._enabled:
                data = self.alpaca.get_price(mapping["alpaca"])
                if data:
                    data["unified_symbol"] = unified_symbol
                    sources.append(data)

            if sources:
                # Use weighted average (Capital primary for forex/commodities)
                results[unified_symbol] = {
                    "symbol": unified_symbol,
                    "type": mapping["type"],
                    "sources": sources,
                    "price": self._consensus_price(sources),
                    "source_count": len(sources),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

        return results

    def _consensus_price(self, sources: List[Dict]) -> float:
        """Calculate consensus price across sources."""
        if not sources:
            return 0
        # Weight: Capital 50%, Binance 30%, Alpaca 20%
        weights = {"capital": 0.5, "binance": 0.3, "alpaca": 0.2}
        total_weight = 0
        weighted_sum = 0
        for s in sources:
            w = weights.get(s["source"], 0.33)
            weighted_sum += s["price"] * w
            total_weight += w
        return weighted_sum / total_weight if total_weight else 0

    def detect_arbitrage(self, unified_symbol: str, data: Dict) -> Optional[Dict]:
        """Detect price discrepancies across exchanges."""
        sources = data.get("sources", [])
        if len(sources) < 2:
            return None

        prices = [s["price"] for s in sources]
        max_p = max(prices)
        min_p = min(prices)
        spread = (max_p - min_p) / min_p if min_p else 0

        if spread > 0.001:  # 0.1% arbitrage opportunity
            return {
                "symbol": unified_symbol,
                "spread_pct": spread * 100,
                "high": max_p,
                "low": min_p,
                "high_source": next(s["source"] for s in sources if s["price"] == max_p),
                "low_source": next(s["source"] for s in sources if s["price"] == min_p),
            }
        return None

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    feed = UnifiedMultiSourceFeed()
    print("Fetching prices from ALL sources...")
    prices = feed.fetch_all()

    print(f"\n{'='*70}")
    print(f"UNIFIED MULTI-SOURCE PRICES")
    print(f"{'='*70}")

    for sym, data in prices.items():
        sources = ", ".join(s["source"] for s in data["sources"])
        print(f"{sym:<12} {data['type']:<10} £${data['price']:<12.4f} [{sources}]")

        arb = feed.detect_arbitrage(sym, data)
        if arb:
            print(f"  ARBITRAGE: {arb['spread_pct']:.3f}% spread ({arb['high_source']} > {arb['low_source']})")

if __name__ == "__main__":
    main()
