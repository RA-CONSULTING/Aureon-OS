#!/usr/bin/env python3
"""
OLLAMA META-COGNITIVE SWITCHBOARD
=================================
Active intelligence layer. Runs independently, feeds the radar.

- Pulls live market data from Capital.com
- Sends structured market snapshots to Ollama
- Receives meta-cognitive analysis (narrative + signals)
- Writes signals to ollama_signals.jsonl (radar consumes)
- Logs market commentary for human review

Usage: python ollama_switchboard.py
"""

import os
import sys
import json
import time
import math
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Optional, Dict, List

import requests

# ─── PATHS ────────────────────────────────────────────────────────────────────
RADAR_DIR = Path(__file__).parent
OLLAMA_CACHE = RADAR_DIR / "ollama_cache"
OLLAMA_CACHE.mkdir(exist_ok=True)
SIGNAL_OUT = RADAR_DIR / "ollama_signals.jsonl"
META_LOG = RADAR_DIR / "ollama_meta.log"

# ─── CONFIG ───────────────────────────────────────────────────────────────────
# ─── OLLAMA CONFIG ────────────────────────────────────────────────────────────
# Use Aureon OS ollama_config for proper cloud/local detection and auth
sys.path.insert(0, str(Path("C:/Users/user/.kimi_openclaw/workspace/aureon-os-upstream")))
try:
    from aureon.ollama_config import (
        resolve_ollama_api_key,
        resolve_ollama_native_base_url,
        ollama_authorization_headers,
        is_ollama_cloud_url,
        OLLAMA_CLOUD_NATIVE_BASE_URL,
    )
    AUREON_CONFIG_AVAILABLE = True
except ImportError:
    AUREON_CONFIG_AVAILABLE = False
    print("[WARN] Aureon ollama_config not available, using fallback")

OLLAMA_URL = os.getenv("OLLAMA_API_URL", OLLAMA_CLOUD_NATIVE_BASE_URL if AUREON_CONFIG_AVAILABLE else "http://localhost:11434")
MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
CAPITAL_API_KEY = os.getenv("CAPITAL_API_KEY")
CAPITAL_IDENTIFIER = os.getenv("CAPITAL_IDENTIFIER")
CAPITAL_PASSWORD = os.getenv("CAPITAL_PASSWORD")

SYMBOLS = ["USDJPY", "US100", "EURUSD", "GBPUSD", "GOLD", "SILVER",
           "OIL_CRUDE", "NATURALGAS", "AAPL", "TSLA", "NVDA", "BTCUSD"]

# ─── DATA STRUCTURES ──────────────────────────────────────────────────────────
@dataclass
class MarketSnapshot:
    symbol: str
    price: float
    bid: float
    ask: float
    spread_pct: float
    change_pct: float
    high: float
    low: float
    timestamp: str

@dataclass
class MetaSignal:
    timestamp: str
    source: str
    symbol: str
    direction: str
    confidence: float
    reasoning: str
    market_narrative: str
    volatility_assessment: str
    risk_level: str
    urgency: str
    fusion_score: float

# ─── CAPITAL.COM DATA FEED ────────────────────────────────────────────────────
# Use the working CapitalClient from the radar (handles auth, caching, retry)
sys.path.insert(0, str(RADAR_DIR))
from capital_client import CapitalClient

class CapitalFeed:
    def __init__(self, demo=False):
        os.environ["CAPITAL_DEMO"] = "1" if demo else "0"
        self.client = CapitalClient()
        
    def snapshot(self, symbol: str) -> Optional[MarketSnapshot]:
        ticker = self.client.get_ticker(symbol)
        if not isinstance(ticker, dict):
            return None
        price = ticker.get("price", 0)
        bid = ticker.get("bid", 0)
        ask = ticker.get("ask", 0)
        if not price:
            return None
        spread = ((ask - bid) / price * 100) if price and bid and ask else 0
        return MarketSnapshot(
            symbol=symbol,
            price=round(float(price), 4),
            bid=round(float(bid), 4),
            ask=round(float(ask), 4),
            spread_pct=round(spread, 4),
            change_pct=round(float(ticker.get("change_pct", 0)), 4),
            high=round(float(ticker.get("high", price)), 4),
            low=round(float(ticker.get("low", price)), 4),
            timestamp=datetime.now(timezone.utc).isoformat()
        )

# ─── OLLAMA META-COGNITIVE ENGINE ─────────────────────────────────────────────
class OllamaMetaEngine:
    def __init__(self):
        self.url = resolve_ollama_native_base_url(OLLAMA_URL) if AUREON_CONFIG_AVAILABLE else OLLAMA_URL
        self.model = MODEL
        self.sess = requests.Session()
        self.sess.timeout = 60
        # Auth headers for Ollama Cloud
        if AUREON_CONFIG_AVAILABLE:
            self.headers = ollama_authorization_headers(self.url)
            self.is_cloud = is_ollama_cloud_url(self.url)
        else:
            self.headers = {}
            self.is_cloud = False

    def _cache_key(self, prompt: str) -> str:
        return hashlib.sha256(prompt.encode()).hexdigest()[:16]

    def _cached(self, key: str) -> Optional[dict]:
        cf = OLLAMA_CACHE / f"{key}.json"
        if cf.exists() and (time.time() - cf.stat().st_mtime) < 120:
            try:
                with open(cf) as f:
                    return json.load(f)
            except:
                pass
        return None

    def _save_cache(self, key: str, data: dict):
        with open(OLLAMA_CACHE / f"{key}.json", 'w') as f:
            json.dump(data, f)

    def analyze(self, snapshots: List[MarketSnapshot]) -> List[MetaSignal]:
        """Send market snapshot array to Ollama, get back meta-cognitive signals."""
        prompt = self._build_prompt(snapshots)
        cache_key = self._cache_key(prompt)
        cached = self._cached(cache_key)
        if cached:
            return self._parse_response(cached, snapshots)

        try:
            req_json = {"model": self.model, "prompt": prompt, "stream": False}
            # For cloud, use json format; for local, format may not be supported by all models
            if self.is_cloud:
                req_json["format"] = "json"
            
            r = self.sess.post(f"{self.url}/api/generate",
                json=req_json, headers=self.headers)
            r.raise_for_status()
            result = r.json()
            raw = result.get("response", "{}")
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = {"raw": raw, "parsed": False}
            self._save_cache(cache_key, parsed)
            return self._parse_response(parsed, snapshots)
        except Exception as e:
            print(f"[OLLAMA ERROR] {e}")
            return []

    def _build_prompt(self, snapshots: List[MarketSnapshot]) -> str:
        data_lines = []
        for s in snapshots:
            data_lines.append(
                f"{s.symbol}: price={s.price}, change={s.change_pct}%, "
                f"spread={s.spread_pct}%, high={s.high}, low={s.low}"
            )
        data_block = "\n".join(data_lines)

        return f"""You are a financial meta-cognitive analyst. Examine this live market data and provide deep insight.

MARKET DATA:
{data_block}

TASK:
1. Identify which instruments show the strongest directional momentum.
2. Detect any anomalies or unusual patterns.
3. Assess overall market volatility regime.
4. Generate actionable trading signals.

Return ONLY valid JSON with this exact structure:
{{
    "market_narrative": "concise summary of what is moving and why",
    "volatility_regime": "LOW|MEDIUM|HIGH|CHAOS",
    "strongest_movers": ["SYMBOL1", "SYMBOL2"],
    "anomalies": ["description of any unusual pattern"],
    "signals": [
        {{
            "symbol": "SYMBOL",
            "direction": "LONG|SHORT|NEUTRAL",
            "confidence": 0.0-1.0,
            "reasoning": "brief rationale",
            "risk_level": "LOW|MEDIUM|HIGH",
            "urgency": "LOW|MEDIUM|HIGH"
        }}
    ]
}}"""

    def _parse_response(self, data: dict, snapshots: List[MarketSnapshot]) -> List[MetaSignal]:
        signals = []
        ts = datetime.now(timezone.utc).isoformat()
        narrative = data.get("market_narrative", "No narrative generated")
        vol_regime = data.get("volatility_regime", "UNKNOWN")

        # Log narrative
        with open(META_LOG, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"TIME: {ts}\n")
            f.write(f"NARRATIVE: {narrative}\n")
            f.write(f"VOLATILITY REGIME: {vol_regime}\n")
            f.write(f"STRONGEST MOVERS: {data.get('strongest_movers', [])}\n")
            f.write(f"ANOMALIES: {data.get('anomalies', [])}\n")
            f.write(f"{'='*60}\n")

        print(f"\n[METACOG] {narrative}")
        print(f"[REGIME]  Volatility: {vol_regime}")

        for sig_data in data.get("signals", []):
            sym = sig_data.get("symbol", "")
            direction = sig_data.get("direction", "NEUTRAL")
            if direction == "NEUTRAL":
                continue
            conf = float(sig_data.get("confidence", 0))
            # Compute fusion score from confidence + narrative weight
            fusion = conf * 1.0  # base; could boost based on narrative strength
            signals.append(MetaSignal(
                timestamp=ts,
                source="ollama_meta_cognitive",
                symbol=sym,
                direction=direction,
                confidence=conf,
                reasoning=sig_data.get("reasoning", ""),
                market_narrative=narrative,
                volatility_assessment=vol_regime,
                risk_level=sig_data.get("risk_level", "MEDIUM"),
                urgency=sig_data.get("urgency", "LOW"),
                fusion_score=round(fusion, 3)
            ))
        return signals

# ─── MAIN SWITCHBOARD LOOP ────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("OLLAMA META-COGNITIVE SWITCHBOARD")
    print("=" * 60)
    
    # Check API key status
    if AUREON_CONFIG_AVAILABLE:
        api_key = resolve_ollama_api_key()
        cloud_url = OLLAMA_CLOUD_NATIVE_BASE_URL
        print(f"Ollama URL:  {OLLAMA_URL}")
        print(f"Cloud URL:   {cloud_url}")
        print(f"Model:       {MODEL}")
        print(f"API Key:     {'CONFIGURED (' + api_key[:4] + '...)' if api_key else 'NOT SET'}")
        if not api_key and is_ollama_cloud_url(OLLAMA_URL):
            print("[WARN] Ollama Cloud selected but no API key found!")
            print("       Set OLLAMA_API_KEY or AUREON_OLLAMA_API_KEY")
    else:
        print(f"Ollama URL:  {OLLAMA_URL}")
        print(f"Model:       {MODEL}")
    
    print(f"Output:      {SIGNAL_OUT}")
    print(f"Meta log:    {META_LOG}")
    print("=" * 60)

    # Check Ollama is reachable
    try:
        headers = ollama_authorization_headers(OLLAMA_URL) if AUREON_CONFIG_AVAILABLE else {}
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5, headers=headers)
        r.raise_for_status()
        models = [m.get("name") for m in r.json().get("models", [])]
        print(f"[OK] Ollama reachable. Models: {models}")
        if MODEL not in models:
            print(f"[WARN] Model '{MODEL}' not found in Ollama. Available: {models}")
    except Exception as e:
        print(f"[FATAL] Cannot reach Ollama at {OLLAMA_URL}: {e}")
        if AUREON_CONFIG_AVAILABLE and is_ollama_cloud_url(OLLAMA_URL):
            print("  Check your OLLAMA_API_KEY for cloud access.")
        else:
            print("  Start Ollama first:  ollama serve")
        sys.exit(1)

    feed = CapitalFeed(demo=False)
    engine = OllamaMetaEngine()
    cycle = 0

    while True:
        cycle += 1
        print(f"\n--- CYCLE {cycle} @ {datetime.now(timezone.utc).isoformat()} ---")

        # Gather snapshots
        snapshots = []
        for sym in SYMBOLS:
            snap = feed.snapshot(sym)
            if snap:
                snapshots.append(snap)
                print(f"  {sym:12s}  price={snap.price:>10.4f}  change={snap.change_pct:>+7.2f}%")

        if not snapshots:
            print("[WARN] No market data. Retrying in 60s...")
            time.sleep(60)
            continue

        # Meta-cognitive analysis
        print("\n[OLLAMA] Querying for meta-cognitive analysis...")
        signals = engine.analyze(snapshots)

        # Write signals
        if signals:
            with open(SIGNAL_OUT, 'a', encoding='utf-8') as f:
                for sig in signals:
                    f.write(json.dumps(asdict(sig)) + "\n")
            print(f"[SIGNALS] Wrote {len(signals)} signals:")
            for s in signals:
                print(f"  -> {s.symbol} {s.direction}  conf={s.confidence:.2f}  "
                      f"urgency={s.urgency}  risk={s.risk_level}")
        else:
            print("[SIGNALS] No actionable signals this cycle.")

        # Cycle interval: phi-scaled (60s base)
        interval = 60 + int(cycle * 0.1) % 60  # 60-120s
        print(f"[SLEEP] Next cycle in {interval}s...")
        time.sleep(interval)

if __name__ == "__main__":
    main()
