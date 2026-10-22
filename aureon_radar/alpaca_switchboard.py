#!/usr/bin/env python3
"""
ALPACA STOCK CORRELATION SWITCHBOARD
====================================
Real-time US stock data + cross-market correlation engine.

- Pulls live stock prices from Alpaca API
- Correlates AAPL, TSLA, NVDA, US100 with crypto (BTC, ETH)
- Correlates with commodities (GOLD, OIL, NATURALGAS)
- Correlates with planetary data (space weather, Schumann)
- Writes signals to stock_signals.jsonl (radar consumes)
- Logs correlation matrix for human review

Usage: python alpaca_switchboard.py
"""

import os
import sys
import json
import time
import math
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
SIGNAL_OUT = RADAR_DIR / "stock_signals.jsonl"
STOCK_LOG = RADAR_DIR / "stock_meta.log"

# ─── API KEYS ─────────────────────────────────────────────────────────────────
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")
ALPACA_PAPER = os.getenv("ALPACA_PAPER", "false").lower() == "true"

# ─── DATA STRUCTURES ──────────────────────────────────────────────────────────
@dataclass
class StockSnapshot:
    timestamp: str
    symbol: str
    price: float
    change_pct: float
    volume: int
    high: float
    low: float
    source: str = "alpaca"

@dataclass
class StockSignal:
    timestamp: str
    source: str
    symbol: str
    direction: str
    confidence: float
    reasoning: str
    correlation_data: Dict
    planetary_alignment: str
    urgency: str

# ─── ALPACA REST API ──────────────────────────────────────────────────────────
class AlpacaFeed:
    """Pull snapshot data from Alpaca REST API"""
    
    BASE = "https://paper-api.alpaca.markets" if ALPACA_PAPER else "https://api.alpaca.markets"
    DATA_BASE = "https://data.alpaca.markets"
    
    def __init__(self):
        self.sess = requests.Session()
        self.sess.timeout = 15
        self.headers = {
            "APCA-API-KEY-ID": ALPACA_API_KEY,
            "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY
        }
    
    def _get(self, endpoint: str, params: dict = None, data=False) -> Optional[dict]:
        base = self.DATA_BASE if data else self.BASE
        try:
            r = self.sess.get(f"{base}{endpoint}", headers=self.headers, params=params, timeout=15)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"[ALPACA ERROR] {endpoint}: {e}")
            return None
    
    def get_snapshot(self, symbol: str) -> Optional[StockSnapshot]:
        """Get latest snapshot for a stock"""
        data = self._get(f"/v2/stocks/{symbol}/snapshot", data=True)
        if not data:
            return None
        
        latest = data.get("latestTrade", {})
        daily = data.get("dailyBar", {})
        prev = data.get("prevDailyBar", {})
        
        price = float(latest.get("p", 0))
        prev_close = float(prev.get("c", price))
        change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0
        
        return StockSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            symbol=symbol,
            price=price,
            change_pct=round(change_pct, 2),
            volume=int(daily.get("v", 0)),
            high=float(daily.get("h", price)),
            low=float(daily.get("l", price))
        )
    
    def get_quotes(self, symbols: List[str]) -> Dict[str, float]:
        """Get latest quotes for multiple symbols"""
        data = self._get("/v2/stocks/quotes/latest", {"symbols": ",".join(symbols)}, data=True)
        if not data or "quotes" not in data:
            return {}
        
        prices = {}
        for sym, quote in data["quotes"].items():
            bid = float(quote.get("bp", 0))
            ask = float(quote.get("ap", 0))
            if bid and ask:
                prices[sym] = round((bid + ask) / 2, 2)
        return prices

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
class StockCorrelationEngine:
    """Correlates US stocks with crypto, commodities, and planetary data"""
    
    def __init__(self):
        self.alpaca = AlpacaFeed()
        self.capital = CapitalCorrelationFeed()
        self.price_history = {}
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
    
    def analyze(self) -> List[StockSignal]:
        """Pull stock + market data, compute correlations, generate signals"""
        signals = []
        ts = datetime.now(timezone.utc).isoformat()
        
        # ─── STOCK DATA ───────────────────────────────────────────────
        stock_symbols = ["AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "GOOGL", "META"]
        stock_data = {}
        
        print("\n[STOCKS] Fetching Alpaca data...")
        for sym in stock_symbols:
            snap = self.alpaca.get_snapshot(sym)
            if snap:
                stock_data[sym] = snap
                self._update_history(sym, snap.price)
                print(f"  {sym}: ${snap.price:,.2f} ({snap.change_pct:+.2f}%)")
        
        # ─── CRYPTO DATA (from Binance cache or fetch) ────────────────
        crypto_symbols = ["BTCUSD", "ETHUSD"]
        crypto_data = {}
        
        print("\n[CRYPTO] Reading from Binance feed...")
        for sym in crypto_symbols:
            # Try to read from Binance correlation log
            price = None
            change = 0
            try:
                # Read latest from correlation_meta.log
                with open(RADAR_DIR / "correlation_meta.log", 'r') as f:
                    lines = f.readlines()
                    for line in reversed(lines):
                        if line.startswith(f"{sym[:-3]}USDT:"):
                            parts = line.strip().split()
                            if len(parts) >= 2:
                                price_str = parts[1].replace("$", "").replace(",", "")
                                price = float(price_str)
                                if len(parts) >= 3:
                                    change_str = parts[2].strip("()")
                                    change = float(change_str.replace("%", ""))
                            break
            except:
                pass
            
            if price:
                crypto_data[sym] = {"price": price, "change": change}
                self._update_history(sym, price)
                print(f"  {sym}: ${price:,.2f} ({change:+.2f}%)")
        
        # ─── COMMODITY DATA ───────────────────────────────────────────
        commodity_symbols = ["GOLD", "OIL_CRUDE", "NATURALGAS"]
        comm_data = {}
        
        print("\n[COMMODITIES] Fetching Capital.com data...")
        for sym in commodity_symbols:
            price = self.capital.get_price(sym)
            if price:
                comm_data[sym] = price
                self._update_history(sym, price)
                print(f"  {sym}: {price:,.2f}")
        
        # ─── CORRELATION ANALYSIS ─────────────────────────────────────
        print("\n[CORRELATION MATRIX]")
        correlations = {}
        
        for stock_sym in stock_data:
            for crypto_sym in crypto_data:
                corr = self._correlation(stock_sym, crypto_sym)
                correlations[f"{stock_sym}:{crypto_sym}"] = corr
                if abs(corr) > 0.3:
                    print(f"  {stock_sym} vs {crypto_sym}: {corr:+.3f}")
            
            for comm_sym in comm_data:
                corr = self._correlation(stock_sym, comm_sym)
                correlations[f"{stock_sym}:{comm_sym}"] = corr
                if abs(corr) > 0.3:
                    print(f"  {stock_sym} vs {comm_sym}: {corr:+.3f}")
        
        # ─── PLANETARY DATA ───────────────────────────────────────────
        planetary_narrative = "Planetary conditions nominal"
        energy_level = "LOW"
        
        planetary_file = RADAR_DIR / "planetary_meta.log"
        if planetary_file.exists():
            try:
                with open(planetary_file, 'r') as f:
                    lines = f.readlines()
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
        # Tech stocks vs BTC correlation
        for stock_sym in ["AAPL", "TSLA", "NVDA"]:
            if stock_sym not in stock_data:
                continue
            
            stock = stock_data[stock_sym]
            
            # vs BTC
            if "BTCUSD" in crypto_data:
                corr_btc = correlations.get(f"{stock_sym}:BTCUSD", 0)
                if abs(corr_btc) > 0.5:
                    direction = "LONG" if corr_btc > 0 else "SHORT"
                    signals.append(StockSignal(
                        timestamp=ts,
                        source="stock_crypto_correlation",
                        symbol=stock_sym,
                        direction=direction,
                        confidence=min(abs(corr_btc), 0.85),
                        reasoning=f"{stock_sym}-BTC correlation: {corr_btc:+.3f}",
                        correlation_data={f"{stock_sym}_btc": corr_btc},
                        planetary_alignment=energy_level,
                        urgency="MEDIUM"
                    ))
            
            # vs GOLD (safe haven)
            corr_gold = correlations.get(f"{stock_sym}:GOLD", 0)
            if corr_gold < -0.4:
                signals.append(StockSignal(
                    timestamp=ts,
                    source="stock_commodity_correlation",
                    symbol=stock_sym,
                    direction="SHORT",
                    confidence=min(abs(corr_gold), 0.8),
                    reasoning=f"{stock_sym}-GOLD inverse correlation: {corr_gold:+.3f} (risk-off)",
                    correlation_data={f"{stock_sym}_gold": corr_gold},
                    planetary_alignment=energy_level,
                    urgency="MEDIUM"
                ))
            
            # Momentum signal
            if stock.change_pct > 3:
                signals.append(StockSignal(
                    timestamp=ts,
                    source="stock_momentum",
                    symbol=stock_sym,
                    direction="LONG",
                    confidence=min(stock.change_pct / 5, 0.9),
                    reasoning=f"{stock_sym} strong momentum: +{stock.change_pct:.2f}%",
                    correlation_data={},
                    planetary_alignment=energy_level,
                    urgency="HIGH"
                ))
            elif stock.change_pct < -3:
                signals.append(StockSignal(
                    timestamp=ts,
                    source="stock_momentum",
                    symbol=stock_sym,
                    direction="SHORT",
                    confidence=min(abs(stock.change_pct) / 5, 0.9),
                    reasoning=f"{stock_sym} negative momentum: {stock.change_pct:.2f}%",
                    correlation_data={},
                    planetary_alignment=energy_level,
                    urgency="HIGH"
                ))
        
        # ─── LOG ──────────────────────────────────────────────────────
        with open(STOCK_LOG, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"TIME: {ts}\n")
            f.write(f"PLANETARY: {planetary_narrative}\n")
            f.write(f"ENERGY: {energy_level}\n")
            for sym, snap in stock_data.items():
                f.write(f"{sym}: ${snap.price:,.2f} ({snap.change_pct:+.2f}%)\n")
            for pair, corr in correlations.items():
                if abs(corr) > 0.3:
                    f.write(f"CORR {pair}: {corr:+.3f}\n")
            f.write(f"SIGNALS: {len(signals)}\n")
            f.write(f"{'='*60}\n")
        
        print(f"\n[PLANETARY] {planetary_narrative}")
        print(f"[SIGNALS] Generated {len(signals)} stock signals")
        
        return signals

# ─── MAIN SWITCHBOARD LOOP ────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("ALPACA STOCK CORRELATION SWITCHBOARD")
    print("=" * 60)
    print(f"Alpaca API Key: {'CONFIGURED' if ALPACA_API_KEY else 'NOT SET'}")
    print(f"Paper Mode:     {ALPACA_PAPER}")
    print(f"Output:         {SIGNAL_OUT}")
    print(f"Stock log:      {STOCK_LOG}")
    print("=" * 60)
    
    if not ALPACA_API_KEY:
        print("[FATAL] Alpaca API key not found. Set ALPACA_API_KEY in .env")
        sys.exit(1)
    
    engine = StockCorrelationEngine()
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
                print(f"  -> {s.symbol} {s.direction}  conf={s.confidence:.2f}")
        else:
            print("[SIGNALS] No stock signals this cycle.")
        
        interval = 120  # 2 minutes
        print(f"[SLEEP] Next cycle in {interval}s...")
        time.sleep(interval)

if __name__ == "__main__":
    main()
