#!/usr/bin/env python3
"""
BINANCE CRYPTO CORRELATION SWITCHBOARD
======================================
Real-time crypto data + cross-market correlation engine.

- Streams live crypto prices from Binance WebSocket
- Correlates BTC/ETH with stocks (US100, AAPL, TSLA, NVDA)
- Correlates with commodities (GOLD, OIL, NATURALGAS)
- Correlates with planetary data (space weather, Schumann)
- Writes signals to crypto_signals.jsonl (radar consumes)
- Logs correlation matrix for human review

Usage: python binance_switchboard.py
"""

import os
import sys
import json
import time
import math
import threading
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Optional, Dict, List
from collections import deque

# Load environment variables from .env
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

import requests

# ─── PATHS ────────────────────────────────────────────────────────────────────
RADAR_DIR = Path(__file__).parent
SIGNAL_OUT = RADAR_DIR / "crypto_signals.jsonl"
CORR_LOG = RADAR_DIR / "correlation_meta.log"

# ─── API KEYS ─────────────────────────────────────────────────────────────────
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")

# ─── DATA STRUCTURES ──────────────────────────────────────────────────────────
@dataclass
class CryptoSnapshot:
    timestamp: str
    symbol: str
    price: float
    change_24h_pct: float
    volume: float
    high: float
    low: float
    source: str = "binance"

@dataclass
class CorrelationSignal:
    timestamp: str
    source: str
    symbol: str
    direction: str
    confidence: float
    reasoning: str
    correlation_data: Dict
    planetary_alignment: str
    urgency: str

# ─── BINANCE REST API (for initial snapshot) ──────────────────────────────────
class BinanceRestFeed:
    """Pull snapshot data from Binance REST API"""
    
    BASE = "https://api.binance.com"
    
    def __init__(self):
        self.sess = requests.Session()
        self.sess.timeout = 15
        self.headers = {}
        if BINANCE_API_KEY:
            self.headers["X-MBX-APIKEY"] = BINANCE_API_KEY
    
    def _get(self, endpoint: str, params: dict = None) -> Optional[dict]:
        try:
            r = self.sess.get(f"{self.BASE}{endpoint}", headers=self.headers, params=params, timeout=15)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"[BINANCE ERROR] {endpoint}: {e}")
            return None
    
    def get_ticker(self, symbol: str) -> Optional[CryptoSnapshot]:
        """Get 24hr ticker for a symbol"""
        data = self._get("/api/v3/ticker/24hr", {"symbol": symbol})
        if not data:
            return None
        return CryptoSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            symbol=symbol,
            price=float(data.get("lastPrice", 0)),
            change_24h_pct=float(data.get("priceChangePercent", 0)),
            volume=float(data.get("volume", 0)),
            high=float(data.get("highPrice", 0)),
            low=float(data.get("lowPrice", 0))
        )
    
    def get_all_tickers(self) -> List[CryptoSnapshot]:
        """Get all 24hr tickers"""
        data = self._get("/api/v3/ticker/24hr")
        if not data or not isinstance(data, list):
            return []
        snapshots = []
        for t in data:
            sym = t.get("symbol", "")
            if sym.endswith("USDT") and not sym.startswith("UP") and not sym.startswith("DOWN"):
                snapshots.append(CryptoSnapshot(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    symbol=sym,
                    price=float(t.get("lastPrice", 0)),
                    change_24h_pct=float(t.get("priceChangePercent", 0)),
                    volume=float(t.get("volume", 0)),
                    high=float(t.get("highPrice", 0)),
                    low=float(t.get("lowPrice", 0))
                ))
        return snapshots

# ─── CAPITAL.COM FEED (for correlation) ───────────────────────────────────────
class CapitalCorrelationFeed:
    """Pull Capital.com prices for cross-market correlation"""
    
    def __init__(self):
        sys.path.insert(0, str(RADAR_DIR))
        from capital_client import CapitalClient
        self.client = CapitalClient()
    
    def get_price(self, symbol: str) -> Optional[float]:
        ticker = self.client.get_ticker(symbol)
        if isinstance(ticker, dict):
            price = ticker.get("price")
            if price:
                return float(price)
        return None

# ─── CORRELATION ENGINE ───────────────────────────────────────────────────────
class CrossMarketCorrelationEngine:
    """Correlates crypto with stocks, commodities, and planetary data"""
    
    def __init__(self):
        self.binance = BinanceRestFeed()
        self.capital = CapitalCorrelationFeed()
        self.price_history = {}  # symbol -> deque of (timestamp, price)
        self.history_len = 20
    
    def _update_history(self, symbol: str, price: float):
        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=self.history_len)
        self.price_history[symbol].append((time.time(), price))
    
    def _correlation(self, sym1: str, sym2: str) -> float:
        """Calculate Pearson correlation between two price histories"""
        h1 = self.price_history.get(sym1, deque())
        h2 = self.price_history.get(sym2, deque())
        if len(h1) < 5 or len(h2) < 5:
            return 0.0
        
        # Use last N common points
        n = min(len(h1), len(h2), 10)
        p1 = [x[1] for x in list(h1)[-n:]]
        p2 = [x[1] for x in list(h2)[-n:]]
        
        if len(p1) != len(p2):
            return 0.0
        
        mean1 = sum(p1) / len(p1)
        mean2 = sum(p2) / len(p2)
        
        num = sum((a - mean1) * (b - mean2) for a, b in zip(p1, p2))
        den1 = sum((a - mean1) ** 2 for a in p1) ** 0.5
        den2 = sum((b - mean2) ** 2 for b in p2) ** 0.5
        
        if den1 == 0 or den2 == 0:
            return 0.0
        return num / (den1 * den2)
    
    def analyze(self) -> List[CorrelationSignal]:
        """Pull crypto + traditional market data, compute correlations, generate signals"""
        signals = []
        ts = datetime.now(timezone.utc).isoformat()
        
        # ─── CRYPTO DATA ──────────────────────────────────────────────
        crypto_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]
        crypto_data = {}
        
        print("\n[CRYPTO] Fetching Binance data...")
        for sym in crypto_symbols:
            snap = self.binance.get_ticker(sym)
            if snap:
                crypto_data[sym] = snap
                self._update_history(sym, snap.price)
                print(f"  {sym}: ${snap.price:,.2f} ({snap.change_24h_pct:+.2f}%)")
        
        # ─── TRADITIONAL MARKET DATA ──────────────────────────────────
        trad_symbols = {
            "US100": "US Tech 100",
            "GOLD": "Gold",
            "OIL_CRUDE": "Crude Oil",
            "NATURALGAS": "Natural Gas",
            "AAPL": "Apple",
            "TSLA": "Tesla",
            "NVDA": "NVIDIA"
        }
        trad_data = {}
        
        print("\n[TRADITIONAL] Fetching Capital.com data...")
        for sym in trad_symbols:
            price = self.capital.get_price(sym)
            if price:
                trad_data[sym] = price
                self._update_history(sym, price)
                print(f"  {sym}: {price:,.2f}")
        
        # ─── CORRELATION ANALYSIS ─────────────────────────────────────
        print("\n[CORRELATION MATRIX]")
        correlations = {}
        
        for crypto_sym in crypto_data:
            for trad_sym in trad_data:
                corr = self._correlation(crypto_sym, trad_sym)
                correlations[f"{crypto_sym}:{trad_sym}"] = corr
                if abs(corr) > 0.3:
                    print(f"  {crypto_sym} vs {trad_sym}: {corr:+.3f}")
        
        # ─── PLANETARY DATA CHECK ─────────────────────────────────────
        planetary_narrative = "Planetary conditions nominal"
        energy_level = "LOW"
        
        # Read latest planetary data if available
        planetary_file = RADAR_DIR / "planetary_meta.log"
        if planetary_file.exists():
            try:
                with open(planetary_file, 'r') as f:
                    lines = f.readlines()
                    # Get last narrative line
                    for line in reversed(lines):
                        if line.startswith("NARRATIVE:"):
                            planetary_narrative = line.replace("NARRATIVE:", "").strip()
                            break
                        if line.startswith("ENERGY LEVEL:"):
                            energy_level = line.replace("ENERGY LEVEL:", "").strip()
                            break
            except:
                pass
        
        # ─── SIGNAL GENERATION ────────────────────────────────────────
        # BTC correlation with tech stocks
        if "BTCUSDT" in crypto_data:
            btc = crypto_data["BTCUSDT"]
            
            # BTC vs US100 correlation
            corr_us100 = correlations.get("BTCUSDT:US100", 0)
            if abs(corr_us100) > 0.5:
                direction = "LONG" if corr_us100 > 0 else "SHORT"
                signals.append(CorrelationSignal(
                    timestamp=ts,
                    source="crypto_correlation",
                    symbol="BTCUSD",
                    direction=direction,
                    confidence=min(abs(corr_us100), 0.9),
                    reasoning=f"BTC-US100 correlation: {corr_us100:+.3f}",
                    correlation_data={"btc_us100": corr_us100},
                    planetary_alignment=energy_level,
                    urgency="MEDIUM"
                ))
            
            # BTC vs GOLD correlation (safe haven)
            corr_gold = correlations.get("BTCUSDT:GOLD", 0)
            if corr_gold < -0.4:
                # Negative correlation with gold = risk-on BTC
                signals.append(CorrelationSignal(
                    timestamp=ts,
                    source="crypto_correlation",
                    symbol="BTCUSD",
                    direction="LONG",
                    confidence=min(abs(corr_gold), 0.8),
                    reasoning=f"BTC-GOLD inverse correlation: {corr_gold:+.3f} (risk-on)",
                    correlation_data={"btc_gold": corr_gold},
                    planetary_alignment=energy_level,
                    urgency="MEDIUM"
                ))
            
            # BTC momentum signal
            if btc.change_24h_pct > 5:
                signals.append(CorrelationSignal(
                    timestamp=ts,
                    source="crypto_momentum",
                    symbol="BTCUSD",
                    direction="LONG",
                    confidence=min(btc.change_24h_pct / 10, 0.9),
                    reasoning=f"BTC strong momentum: +{btc.change_24h_pct:.2f}% (24h)",
                    correlation_data={},
                    planetary_alignment=energy_level,
                    urgency="HIGH"
                ))
            elif btc.change_24h_pct < -5:
                signals.append(CorrelationSignal(
                    timestamp=ts,
                    source="crypto_momentum",
                    symbol="BTCUSD",
                    direction="SHORT",
                    confidence=min(abs(btc.change_24h_pct) / 10, 0.9),
                    reasoning=f"BTC negative momentum: {btc.change_24h_pct:.2f}% (24h)",
                    correlation_data={},
                    planetary_alignment=energy_level,
                    urgency="HIGH"
                ))
        
        # ETH correlation with tech
        if "ETHUSDT" in crypto_data and "NVDA" in trad_data:
            corr_eth_nvda = correlations.get("ETHUSDT:NVDA", 0)
            if abs(corr_eth_nvda) > 0.4:
                direction = "LONG" if corr_eth_nvda > 0 else "SHORT"
                signals.append(CorrelationSignal(
                    timestamp=ts,
                    source="crypto_correlation",
                    symbol="ETHUSD",
                    direction=direction,
                    confidence=min(abs(corr_eth_nvda), 0.8),
                    reasoning=f"ETH-NVDA correlation: {corr_eth_nvda:+.3f}",
                    correlation_data={"eth_nvda": corr_eth_nvda},
                    planetary_alignment=energy_level,
                    urgency="MEDIUM"
                ))
        
        # ─── LOG ──────────────────────────────────────────────────────
        with open(CORR_LOG, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"TIME: {ts}\n")
            f.write(f"PLANETARY: {planetary_narrative}\n")
            f.write(f"ENERGY: {energy_level}\n")
            for crypto_sym, snap in crypto_data.items():
                f.write(f"{crypto_sym}: ${snap.price:,.2f} ({snap.change_24h_pct:+.2f}%)\n")
            for pair, corr in correlations.items():
                if abs(corr) > 0.3:
                    f.write(f"CORR {pair}: {corr:+.3f}\n")
            f.write(f"SIGNALS: {len(signals)}\n")
            f.write(f"{'='*60}\n")
        
        print(f"\n[PLANETARY] {planetary_narrative}")
        print(f"[SIGNALS] Generated {len(signals)} correlation signals")
        
        return signals

# ─── MAIN SWITCHBOARD LOOP ────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("BINANCE CRYPTO CORRELATION SWITCHBOARD")
    print("=" * 60)
    print(f"Binance API Key: {'CONFIGURED' if BINANCE_API_KEY else 'NOT SET'}")
    print(f"Output:          {SIGNAL_OUT}")
    print(f"Correlation log: {CORR_LOG}")
    print("=" * 60)
    
    if not BINANCE_API_KEY:
        print("[FATAL] Binance API key not found. Set BINANCE_API_KEY in .env")
        sys.exit(1)
    
    engine = CrossMarketCorrelationEngine()
    cycle = 0
    
    while True:
        cycle += 1
        print(f"\n--- CYCLE {cycle} @ {datetime.now(timezone.utc).isoformat()} ---")
        
        signals = engine.analyze()
        
        if signals:
            with open(SIGNAL_OUT, 'a', encoding='utf-8') as f:
                for sig in signals:
                    f.write(json.dumps(asdict(sig)) + "\n")
            print(f"[SIGNALS] Wrote {len(signals)} signals:")
            for s in signals:
                print(f"  -> {s.symbol} {s.direction}  conf={s.confidence:.2f}  "
                      f"reason: {s.reasoning[:60]}...")
        else:
            print("[SIGNALS] No correlation signals this cycle.")
        
        interval = 120  # 2 minutes
        print(f"[SLEEP] Next cycle in {interval}s...")
        time.sleep(interval)

if __name__ == "__main__":
    main()
