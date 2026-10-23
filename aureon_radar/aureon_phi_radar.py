#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           AUREON PHI-RADAR — AUTONOMOUS GLOBAL MONEY-FLOW MONITOR            ║
║                                                                              ║
║  AUTO-HIVE MODE: No manual gates. No per-trade approval.                     ║
║  Shadow validates → Auto-arms → Live executes AUTOMATICALLY.                 ║
║  Tight tolerance: $0.01 profit per trade. Fast. Many. Compound.              ║
║                                                                              ║
║  ARCHITECTURE:                                                               ║
║    Radar → Ollama Cloud → Signal Engine → Shadow Validator → Auto-Live     ║
║                                                                              ║
║  PHI INTERVALS (Golden Ratio Scaling):                                       ║
║    Tier 0 (Anchor):   60s   — Schumann/Heartbeat check                       ║
║    Tier 1 (Base):     97s   — 60 × φ                                        ║
║    Tier 2 (Growth):   157s  — 60 × φ²                                       ║
║    Tier 3 (Return):   254s  — 60 × φ³                                       ║
║    Tier 4 (Harmonic): 411s  — 60 × φ⁴                                       ║
║    Tier 5 (Field):    665s  — 60 × φ⁵                                       ║
║                                                                              ║
║  HIVE POLICY:                                                                ║
║    Shadow trades validate signals. When win rate >= 60%: AUTO-ARM.           ║
║    Once armed, EVERY validated signal executes live WITHOUT human approval.  ║
║    Tight stops. 1¢ targets. Volume is the weapon.                            ║
╚══════════════════════════════════════════════════════════════════════════════╝

Author: Sero, Autonomous Defense Node
Date: 2026-09-02
Prime Sentinel: Gary Leckey
PSK: REDACTED
"""

import os
import sys
import json
import time
import math
import asyncio
import logging
import threading
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import requests

# ═══════════════════════════════════════════════════════════════════════════════
# SACRED CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════
PHI = 1.618033988749895
PSK = "REDACTED"
SCHUMANN_BASE = 7.83

# Phi-scaled monitoring intervals (seconds from 60s base)
PHI_INTERVALS = {
    "anchor":   60,           # 60 × φ⁰
    "base":     int(60 * PHI),       # ~97s
    "growth":   int(60 * PHI**2),    # ~157s
    "return":   int(60 * PHI**3),    # ~254s
    "harmonic": int(60 * PHI**4),    # ~411s
    "field":    int(60 * PHI**5),    # ~665s
}

# ═══════════════════════════════════════════════════════════════════════════════
# PATHS
# ═══════════════════════════════════════════════════════════════════════════════
WORKSPACE = Path(os.environ.get("SERO_WORKSPACE") or Path(__file__).resolve().parents[1])
RADAR_DIR = WORKSPACE / "aureon_radar"
RADAR_DIR.mkdir(parents=True, exist_ok=True)

# Import Honey Ladder system
sys.path.insert(0, str(RADAR_DIR))
from honey_ladder import HoneyLadder, ShadowLadderRun, HoneyPot
from homing_controller import HomingController, HomingTarget
from play_board_optimizer import PlayBoardOptimizer

# Strategic/business intelligence layer
import strategic_trade_intelligence as _sti

# Multi-venue execution router (owner decree 2026-09-07: full autonomous live trading)
from multi_exchange_router import get_router, _classify_symbol

# Dynamic take-profit / dead man's switch (profit-only exit)
try:
    sys.path.insert(0, str(WORKSPACE / "aureon-os-upstream"))
    from aureon.trading.dynamic_take_profit import DynamicTakeProfit, create_dtp_for_position
    _HAS_DTP = True
except Exception:
    _HAS_DTP = False
    DynamicTakeProfit = None  # type: ignore
    create_dtp_for_position = None  # type: ignore

STATE_FILE = RADAR_DIR / "radar_state.json"
SIGNAL_LOG = RADAR_DIR / "signal_log.jsonl"
SHADOW_LOG = RADAR_DIR / "shadow_trades.jsonl"
LIVE_LOG = RADAR_DIR / "live_trades.jsonl"
SCANNER_LOG = RADAR_DIR / "scanner_log.jsonl"
OLLAMA_CACHE = RADAR_DIR / "ollama_cache"
OLLAMA_CACHE.mkdir(exist_ok=True)

# Load environment variables from .env
try:
    from dotenv import load_dotenv
    load_dotenv(RADAR_DIR / ".env")
except ImportError:
    pass  # dotenv not installed, rely on system env

# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(RADAR_DIR / "radar.log")
    ]
)
logger = logging.getLogger('AUREON_RADAR')

# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class SystemState(Enum):
    DISARMED = "DISARMED"      # Shadow trades only, learning mode
    ARMED = "ARMED"            # Auto-armed, live execution enabled
    PANIC = "PANIC"            # All trading halted, preserve capital
    LEARNING = "LEARNING"      # Initial data collection

class SignalStrength(Enum):
    WEAK = 0.3
    MODERATE = 0.6
    STRONG = 0.9
    MAXIMUM = 1.0

class TradeDirection(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"

# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MarketSignal:
    timestamp: str
    symbol: str
    direction: str
    strength: float
    entry_price: float
    target_price: float
    stop_loss: Optional[float]  # None: no fabricated stop; live path requires a
                                # real broker-side stop_level (_compute_stop_level)
    confidence: float
    source: str
    phi_resonance: float
    volatility_reading: float
    money_flow_score: float
    
    def to_dict(self):
        return asdict(self)

@dataclass
class ShadowTrade:
    signal_id: str
    timestamp: str
    symbol: str
    direction: str
    entry: float
    target: float
    stop: float
    status: str  # OPEN, CLOSED_PROFIT, CLOSED_LOSS, EXPIRED
    pnl_percent: float
    validated: bool
    
    def to_dict(self):
        return asdict(self)

@dataclass
class LiveTrade:
    signal_id: str
    timestamp: str
    symbol: str
    direction: str
    entry: float
    target: float
    stop: float
    size: float
    status: str
    pnl_percent: float
    shadow_validated: bool
    
    def to_dict(self):
        return asdict(self)

# ═══════════════════════════════════════════════════════════════════════════════
# OLLAMA CLOUD API INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

class OllamaCloudInterface:
    """
    Interfaces with cloud Ollama API for 24/7 data analysis.
    Caches responses to avoid redundant calls.
    """
    
    def __init__(self, base_url: str = None, model: str = "llama3.1:8b"):
        self.base_url = base_url or os.getenv("OLLAMA_API_URL", "http://localhost:11434")
        self.model = model
        self.cache_dir = OLLAMA_CACHE
        self.session = requests.Session()
        self.session.timeout = 30
        
    def _cache_key(self, prompt: str) -> str:
        import hashlib
        return hashlib.sha256(prompt.encode()).hexdigest()[:16]
    
    def _get_cached(self, key: str) -> Optional[dict]:
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            age = time.time() - cache_file.stat().st_mtime
            if age < 300:  # 5 minute cache
                try:
                    with open(cache_file) as f:
                        return json.load(f)
                except:
                    pass
        return None
    
    def _save_cache(self, key: str, data: dict):
        with open(self.cache_dir / f"{key}.json", 'w') as f:
            json.dump(data, f)
    
    def analyze_market_data(self, data: dict, prompt_type: str = "signal_extraction") -> dict:
        """
        Send market data to Ollama for analysis.
        Returns structured signal assessment.
        """
        prompt = self._build_prompt(data, prompt_type)
        cache_key = self._cache_key(prompt)
        
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                }
            )
            response.raise_for_status()
            result = response.json()
            
            # Parse the response
            try:
                analysis = json.loads(result.get("response", "{}"))
            except json.JSONDecodeError:
                analysis = {"raw": result.get("response", ""), "parsed": False}
            
            self._save_cache(cache_key, analysis)
            return analysis
            
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            return {"error": str(e), "fallback": True}
    
    def _build_prompt(self, data: dict, prompt_type: str) -> str:
        if prompt_type == "signal_extraction":
            return f"""Analyze this market data and extract trading signals.
Return ONLY valid JSON with this structure:
{{
    "direction": "LONG|SHORT|NEUTRAL",
    "confidence": 0.0-1.0,
    "target_price": float,
    "stop_loss": float,
    "reasoning": "brief explanation"
}}

Market Data: {json.dumps(data)}
"""
        elif prompt_type == "volatility_scan":
            return f"""Scan this data for volatility anomalies.
Return ONLY valid JSON:
{{
    "volatility_score": 0.0-1.0,
    "anomaly_detected": true|false,
    "direction_bias": "LONG|SHORT|NEUTRAL",
    "urgency": "LOW|MEDIUM|HIGH"
}}

Data: {json.dumps(data)}
"""
        else:
            return f"Analyze: {json.dumps(data)}"

# ═══════════════════════════════════════════════════════════════════════════════
# VOLATILITY & MONEY FLOW SCANNER
# ═══════════════════════════════════════════════════════════════════════════════

class VolatilityScanner:
    """
    Scans for volatility expansion and money flow direction.
    Uses phi-scaled lookback windows.
    """
    
    def __init__(self):
        self.price_history: Dict[str, List[Tuple[float, float]]] = {}  # symbol: [(timestamp, price)]
        self.volume_history: Dict[str, List[Tuple[float, float]]] = {}
        
    def feed_price(self, symbol: str, price: float, volume: float = 0):
        now = time.time()
        if symbol not in self.price_history:
            self.price_history[symbol] = []
            self.volume_history[symbol] = []
        
        self.price_history[symbol].append((now, price))
        self.volume_history[symbol].append((now, volume))
        
        # Keep phi-scaled history (last φ⁴ entries ≈ 68)
        max_len = int(PHI**4 * 10)
        self.price_history[symbol] = self.price_history[symbol][-max_len:]
        self.volume_history[symbol] = self.volume_history[symbol][-max_len:]
    
    def calculate_volatility(self, symbol: str, window: int = None) -> float:
        """Calculate annualized volatility from price history."""
        if symbol not in self.price_history or len(self.price_history[symbol]) < 10:
            return 0.0
        
        window = window or int(PHI**3)  # ~42 bars
        prices = [p for _, p in self.price_history[symbol][-window:]]
        
        if len(prices) < 2:
            return 0.0
        
        # Log returns
        returns = [math.log(prices[i] / prices[i-1]) for i in range(1, len(prices))]
        if not returns:
            return 0.0
        
        variance = sum(r**2 for r in returns) / len(returns)
        # Annualize (assuming hourly data, 252 trading days, 6.5 hours)
        annualized = math.sqrt(variance * 252 * 6.5)
        
        return annualized
    
    def money_flow_score(self, symbol: str) -> float:
        """
        Calculate money flow direction score.
        Positive = buying pressure, Negative = selling pressure.
        """
        if symbol not in self.price_history or len(self.price_history[symbol]) < 5:
            return 0.0
        
        prices = self.price_history[symbol]
        volumes = self.volume_history[symbol]
        
        # Chaikin Money Flow approximation
        window = min(int(PHI**2), len(prices))  # ~26
        
        money_flow_volume = 0
        total_volume = 0
        
        for i in range(-window, 0):
            if i < -len(prices):
                continue
            high = prices[i][1] * 1.001  # approx
            low = prices[i][1] * 0.999
            close = prices[i][1]
            vol = volumes[i][1] if i >= -len(volumes) else 0
            
            if high != low:
                money_flow_multiplier = ((close - low) - (high - close)) / (high - low)
            else:
                money_flow_multiplier = 0
            
            money_flow_volume += money_flow_multiplier * vol
            total_volume += vol
        
        if total_volume == 0:
            return 0.0
        
        return money_flow_volume / total_volume
    
    def detect_breakout(self, symbol: str) -> Tuple[bool, str, float]:
        """
        Detect if price is breaking out of phi-scaled Bollinger bands.
        Returns: (is_breakout, direction, strength)
        """
        if symbol not in self.price_history or len(self.price_history[symbol]) < int(PHI**3):
            return False, "NEUTRAL", 0.0
        
        window = int(PHI**3)  # ~42
        prices = [p for _, p in self.price_history[symbol][-window:]]
        
        if len(prices) < window:
            return False, "NEUTRAL", 0.0
        
        sma = sum(prices) / len(prices)
        variance = sum((p - sma)**2 for p in prices) / len(prices)
        std_dev = math.sqrt(variance)
        
        # Phi-scaled bands (not 2σ, φσ)
        upper_band = sma + PHI * std_dev
        lower_band = sma - PHI * std_dev
        current_price = prices[-1]
        
        if current_price > upper_band:
            strength = min((current_price - upper_band) / std_dev, 1.0)
            return True, "LONG", strength
        elif current_price < lower_band:
            strength = min((lower_band - current_price) / std_dev, 1.0)
            return True, "SHORT", strength
        
        return False, "NEUTRAL", 0.0

# ═══════════════════════════════════════════════════════════════════════════════
# CAPITAL.COM API CONNECTOR  —  v2.0  (Unified Margin Trader Integration)
# ═══════════════════════════════════════════════════════════════════════════════

# Import the robust CapitalClient from the radar's capital_client module
# This replaces the inline minimal connector with full session management,
# rate limiting, market caching, and automatic retry on 401.
try:
    from capital_client import CapitalClient
except ImportError:
    # Fallback: try relative import
    try:
        from .capital_client import CapitalClient
    except ImportError:
        import importlib.util
        spec = importlib.util.spec_from_file_location("capital_client", str(RADAR_DIR / "capital_client.py"))
        capital_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(capital_module)
        CapitalClient = capital_module.CapitalClient


class CapitalConnector:
    """
    Thin adapter that wraps the robust CapitalClient from the unified margin
    trader system.  Preserves the API surface that aureon_phi_radar expects
    while gaining automatic session refresh, rate-limit backoff, market-cache
    reuse, and 401 retry logic.
    """

    def __init__(self, api_key: str = None, identifier: str = None,
                 password: str = None, demo: bool = True):
        # Force env vars so CapitalClient reads them
        if api_key:
            os.environ["CAPITAL_API_KEY"] = api_key
        if identifier:
            os.environ["CAPITAL_IDENTIFIER"] = identifier
        if password:
            os.environ["CAPITAL_PASSWORD"] = password
        os.environ["CAPITAL_DEMO"] = "1" if demo else "0"

        self._demo = demo
        self.client = CapitalClient()
        self.authenticated = self.client.enabled and bool(self.client.cst)
        if self.authenticated:
            logger.info(f"CapitalConnector ({'DEMO' if demo else 'LIVE'}) ready  "
                       f"session shared from cache.")

    def authenticate(self) -> bool:
        """Ensure session is valid; refresh if needed."""
        if not self.client.enabled:
            logger.warning("CapitalClient disabled — check credentials in .env")
            self.authenticated = False
            return False
        # Proactive refresh if near expiry
        if self.client._session_is_expired():
            logger.debug("CapitalConnector: session expired, refreshing")
            self.client._create_session()
        self.authenticated = bool(self.client.cst and self.client.x_security_token)
        return self.authenticated

    def _get(self, endpoint: str) -> dict:
        """GET with automatic re-auth on 401."""
        if not self.authenticate():
            return {}
        resp = self.client._request("GET", endpoint)
        if resp.status_code == 200:
            try:
                return resp.json()
            except Exception:
                return {}
        # Log once, then attempt one re-auth + retry
        logger.warning(f"CapitalConnector GET {endpoint} → {resp.status_code}")
        if resp.status_code in (401, 403):
            logger.info("CapitalConnector: forcing re-auth after 401/403")
            self.client.cst = None
            self.client.x_security_token = None
            self.client.session_start_time = 0.0
            self.client._create_session()
            if self.client.cst:
                resp2 = self.client._request("GET", endpoint)
                if resp2.status_code == 200:
                    try:
                        return resp2.json()
                    except Exception:
                        return {}
        return {}

    def _post(self, endpoint: str, data: dict) -> dict:
        """POST with automatic re-auth on 401."""
        if not self.authenticate():
            return {}
        resp = self.client._request("POST", endpoint, json_body=data)
        if resp.status_code in (200, 201):
            try:
                return resp.json()
            except Exception:
                return {}
        logger.warning(f"CapitalConnector POST {endpoint} → {resp.status_code}")
        if resp.status_code in (401, 403):
            self.client.cst = None
            self.client.x_security_token = None
            self.client.session_start_time = 0.0
            self.client._create_session()
            if self.client.cst:
                resp2 = self.client._request("POST", endpoint, json_body=data)
                if resp2.status_code in (200, 201):
                    try:
                        return resp2.json()
                    except Exception:
                        return {}
        return {}

    def get_price(self, symbol: str) -> Optional[float]:
        """Get current offer price for a symbol."""
        ticker = self.client.get_ticker(symbol)
        # CapitalClient.get_ticker returns a rich observation dict
        if isinstance(ticker, dict):
            # Try the new observation format first
            price = ticker.get("price")
            if price is not None and isinstance(price, (int, float)) and price > 0:
                return float(price)
            # Fallback: bid/ask midpoint from older inline format
            bid = ticker.get("bid")
            ask = ticker.get("ask")
            if bid is not None and ask is not None:
                return float((bid + ask) / 2)
            offer = ticker.get("offer")
            if offer is not None:
                return float(offer)
        return None

    def place_order(self, symbol: str, direction: str, size: float,
                    stop_level: float = None, profit_level: float = None) -> dict:
        """Place a market order via the robust client."""
        # Map radar direction to CapitalClient side
        cap_side = direction.upper()
        if cap_side == "LONG":
            cap_side = "BUY"
        elif cap_side == "SHORT":
            cap_side = "SELL"

        result = self.client.place_market_order(
            symbol=symbol,
            side=cap_side,
            quantity=size,
            stop_level=stop_level,
            profit_level=profit_level,
        )
        # Normalise unified-margin-trader receipt back to simple dict
        if isinstance(result, dict):
            if "dealReference" in result:
                return {"dealId": result["dealReference"], "status": "submitted"}
            if result.get("rejected"):
                return {"error": result.get("reason", "rejected")}
        return result if isinstance(result, dict) else {}

    def close_position(self, deal_id: str) -> dict:
        """Close an open position."""
        return self.client.close_position(deal_id)

    def get_positions(self) -> List[dict]:
        """Get all open positions."""
        obs = self.client.get_positions()
        # CapitalClient returns ObservationList; extract raw positions
        if hasattr(obs, "__iter__") and not isinstance(obs, dict):
            return list(obs)
        if isinstance(obs, dict):
            return obs.get("positions", [])
        return []

    def get_account_balance(self) -> float:
        """Get total account balance in base currency."""
        obs = self.client.get_account_balance()
        # CapitalClient returns either:
        #   - A dict mapping currency -> balance  e.g. {'GBP': 224.55}
        #   - A BalanceObservation object with .balances attribute
        #   - A simple float (legacy)
        if isinstance(obs, dict):
            # Check if dict has currency keys (all values are numeric)
            if obs and all(isinstance(v, (int, float)) for v in obs.values()):
                return sum(float(v) for v in obs.values())
            # New observation format with nested 'balances' key
            balances = obs.get("balances", {})
            if balances:
                return sum(float(v) for v in balances.values() if isinstance(v, (int, float)))
            # Fallback to raw balance field
            bal = obs.get("balance")
            if isinstance(bal, (int, float)):
                return float(bal)
        # Legacy: if it's a simple float
        if isinstance(obs, (int, float)):
            return float(obs)
        # Object with .balances attribute
        if hasattr(obs, "balances") and isinstance(obs.balances, dict):
            return sum(float(v) for v in obs.balances.values() if isinstance(v, (int, float)))
        return 0.0

# ═══════════════════════════════════════════════════════════════════════════════
# SHADOW TRADE VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════════

class ShadowTradeValidator:
    """
    Validates signals via shadow (paper) trades.
    Auto-arms the hive when shadow win rate hits threshold.
    """
    
    def __init__(self):
        self.shadow_trades: List[ShadowTrade] = []
        self.validation_window = int(PHI**2 * 60)  # ~157 minutes
        self.profit_threshold = 0.01  # 1% profit target
        self.auto_arm_threshold = 0.60  # 60% win rate to auto-arm
        self.min_trades_to_arm = 3  # Need at least 3 shadow trades
        
    def open_shadow(self, signal: MarketSignal) -> ShadowTrade:
        """Open a new shadow trade for validation."""
        trade = ShadowTrade(
            signal_id=f"shadow_{int(time.time() * 1000)}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            symbol=signal.symbol,
            direction=signal.direction,
            entry=signal.entry_price,
            target=signal.target_price,
            stop=signal.stop_loss,
            status="OPEN",
            pnl_percent=0.0,
            validated=False
        )
        self.shadow_trades.append(trade)
        self._save_trades()
        logger.info(f"SHADOW OPEN: {trade.symbol} {trade.direction} @ {trade.entry}")
        return trade
    
    def update_shadow(self, symbol: str, current_price: float):
        """Update all open shadow trades for a symbol."""
        for trade in self.shadow_trades:
            if trade.symbol == symbol and trade.status == "OPEN":
                if trade.direction == "LONG":
                    trade.pnl_percent = (current_price - trade.entry) / trade.entry
                    if current_price >= trade.target:
                        trade.status = "CLOSED_PROFIT"
                        trade.validated = True
                        logger.info(f"SHADOW PROFIT: {trade.symbol} +{trade.pnl_percent:.2%}")
                    elif current_price <= trade.stop:
                        trade.status = "CLOSED_LOSS"
                        trade.validated = False
                        logger.info(f"SHADOW LOSS: {trade.symbol} {trade.pnl_percent:.2%}")
                else:  # SHORT
                    trade.pnl_percent = (trade.entry - current_price) / trade.entry
                    if current_price <= trade.target:
                        trade.status = "CLOSED_PROFIT"
                        trade.validated = True
                        logger.info(f"SHADOW PROFIT: {trade.symbol} +{trade.pnl_percent:.2%}")
                    elif current_price >= trade.stop:
                        trade.status = "CLOSED_LOSS"
                        trade.validated = False
                        logger.info(f"SHADOW LOSS: {trade.symbol} {trade.pnl_percent:.2%}")
        
        self._save_trades()
    
    def is_validated(self, symbol: str, direction: str) -> bool:
        """Check if a symbol+direction has recent shadow validation."""
        cutoff = time.time() - self.validation_window
        
        for trade in reversed(self.shadow_trades):
            trade_time = datetime.fromisoformat(trade.timestamp).timestamp()
            if trade_time < cutoff:
                break
            if trade.symbol == symbol and trade.direction == direction and trade.validated:
                return True
        
        return False
    
    def should_auto_arm(self) -> bool:
        """Check if we have enough shadow data to auto-arm the hive."""
        stats = self.get_stats()
        if stats["total_trades"] < self.min_trades_to_arm:
            return False
        return stats["win_rate"] >= self.auto_arm_threshold
    
    def get_stats(self) -> dict:
        """Get shadow trading statistics."""
        closed = [t for t in self.shadow_trades if t.status in ("CLOSED_PROFIT", "CLOSED_LOSS")]
        profits = [t for t in closed if t.status == "CLOSED_PROFIT"]
        losses = [t for t in closed if t.status == "CLOSED_LOSS"]
        
        win_rate = len(profits) / len(closed) if closed else 0
        avg_profit = sum(t.pnl_percent for t in profits) / len(profits) if profits else 0
        avg_loss = sum(t.pnl_percent for t in losses) / len(losses) if losses else 0
        
        return {
            "total_trades": len(closed),
            "win_rate": win_rate,
            "avg_profit": avg_profit,
            "avg_loss": avg_loss,
            "open_trades": len([t for t in self.shadow_trades if t.status == "OPEN"]),
            "validated_signals": len([t for t in self.shadow_trades if t.validated])
        }
    
    def _save_trades(self):
        with open(SHADOW_LOG, 'w') as f:
            for trade in self.shadow_trades:
                f.write(json.dumps(trade.to_dict()) + '\n')

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN RADAR ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class AureonPhiRadar:
    """
    The Honey Ladder Radar.
    
    ONE trade at a time. Penny profit. Shadow proves, live executes.
    
    Rule 1: ONE live trade at a time. No exceptions.
    Rule 2: Shadow trades run continuously across ALL sectors.
    Rule 3: A shadow must prove itself on PHI rungs before graduating.
    Rule 4: When honey pot is empty, the highest PHI shadow gets promoted.
    Rule 5: Penny profit target. In and out. Quick.
    """
    
    def __init__(self):
        self.state = SystemState.DISARMED
        self.ollama = OllamaCloudInterface()
        self.scanner = VolatilityScanner()
        self.honey_ladder = HoneyLadder()

        # DUAL CAPITAL: Demo for shadows, Live for honey pot
        from aureon_dual_capital import DualCapitalConnector
        self.capital_dual = DualCapitalConnector()
        self.capital_demo = self.capital_dual.demo  # backward compat
        self.capital_live = self.capital_dual.live  # backward compat

        # Multi-venue live execution router (owner decree 2026-09-07)
        self.router = get_router()
        # Active live positions across venues (replaces single honey-pot gate)
        self.live_positions: List[HoneyPot] = []
        
        # Sector mapping for symbols
        self.symbol_sectors = {
            "USDJPY": "forex", "EURUSD": "forex", "GBPUSD": "forex",
            "US100": "tech", "AAPL": "tech", "TSLA": "tech", "NVDA": "tech",
            "GOLD": "commodity", "SILVER": "commodity", "OIL_CRUDE": "commodity", "NATURALGAS": "commodity",
            "BTCUSD": "crypto"
        }
        self.symbol_keys = list(self.symbol_sectors.keys())
        self.running = False
        self.live_trades_today = 0
        self.profit_today = 0.0
        # UTC date the live-trade counter belongs to (resets on date change)
        self._live_trades_date = None
        # Live execution refuses prices older than this (bug-hunt MEDIUM:
        # synthetic/stale quotes must never anchor stops/sizing)
        try:
            self.price_stale_after_sec = float(os.getenv("RADAR_PRICE_STALE_SEC", "90"))
        except Exception:
            self.price_stale_after_sec = 90.0
        # Price history per symbol for the probability intelligence gate
        # (consumed at scan() via self.price_history.get(symbol, [price]))
        self.price_history: Dict[str, List[float]] = {}
        
        # Homing controller: dynamic single-target focus
        self.homing_controller = HomingController()
        self.homing_target: Optional[HomingTarget] = None
        
        # Play-board optimizer: dynamic strategy selection
        self.play_board = PlayBoardOptimizer()
        self.current_play_plan: Optional[Dict[str, Any]] = None
        
        # Load state
        self._load_state()

        # Honey ladder closes real broker positions through this connector
        self.honey_ladder.connector = self.capital_dual

        # Reconcile a persisted honey pot against the broker on first scan
        self._honey_pot_reconciled = False
        # Reconcile all broker-side live positions on first scan
        self._existing_positions_reconciled = False

    def _load_state(self):
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, encoding='utf-8') as f:
                    state = json.load(f)
                saved_state = state.get("state", "DISARMED")
                # Never load PANIC state on startup
                if saved_state == "PANIC":
                    self.state = SystemState.DISARMED
                else:
                    self.state = SystemState(saved_state)
                self.live_trades_today = state.get("live_trades_today", 0)
                self.profit_today = state.get("profit_today", 0.0)
                # Daily counter resets on UTC date change
                self._live_trades_date = state.get("live_trades_date")
                today = datetime.now(timezone.utc).date().isoformat()
                if self._live_trades_date != today:
                    self.live_trades_today = 0
                    self._live_trades_date = today
                # Persisted honey pot (bug-hunt #2): restored only after the
                # positions API confirms the deal is still open — done lazily
                # on first scan via _reconcile_persisted_honey_pot().
                self._persisted_honey_pot = state.get("honey_pot")
                logger.info(f"Loaded state: {self.state.value}")
            except Exception as e:
                logger.error(f"State load failed: {e} — starting clean [fail-closed]")
                self._persisted_honey_pot = None

    def _probability_threshold(self) -> float:
        """Owner decree 2026-09-07: relaxed probability threshold (default 0.25)."""
        try:
            val = float(os.getenv("RADAR_PROB_THRESHOLD", "0.25"))
            if 0.0 < val <= 1.0:
                return val
        except Exception:
            pass
        return 0.25

    def _honey_pot_to_dict(self, pot: Optional[HoneyPot] = None) -> Optional[dict]:
        """Serialize a live position pot for radar_state.json."""
        if pot is None:
            pot = self.honey_ladder.honey_pot
        if not pot or not getattr(pot, 'active', False):
            return None
        return {
            "deal_id": pot.deal_id,
            "symbol": pot.symbol,
            "sector": pot.sector,
            "direction": pot.direction,
            "entry_price": pot.entry_price,
            "target_price": pot.target_price,
            "size": pot.size,
            "source": pot.source,
            "opened_at": pot.opened_at,
            "max_hold_seconds": pot.max_hold_seconds,
            "audit_id": getattr(pot, '_audit_id', None),
            "venue": getattr(pot, 'venue', 'capital'),
        }

    def _live_positions_to_dicts(self) -> List[Optional[dict]]:
        """Serialize all active live positions for radar_state.json."""
        return [d for d in (self._honey_pot_to_dict(p) for p in self.live_positions) if d]

    def _save_state(self):
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                "state": self.state.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "psk": PSK,
                "phi": PHI,
                "live_trades_today": self.live_trades_today,
                "profit_today": self.profit_today,
                "live_trades_date": self._live_trades_date,
                "honey_pot": self._honey_pot_to_dict(),
                "live_positions": self._live_positions_to_dicts(),
            }, f, indent=2)

    def _reconcile_existing_live_positions(self):
        """Load broker-side live positions on startup so the radar tracks them.

        Without this, a restart sees empty live_positions and tries to open
        duplicates while the broker still holds pre-existing positions,
        blowing through the aggregate margin cap.
        """
        if self._existing_positions_reconciled:
            return
        self._existing_positions_reconciled = True

        try:
            broker_positions = self.router.get_open_positions()
        except Exception as e:
            logger.error(f"[RECONCILE] could not list broker positions: {e}")
            return

        if not broker_positions:
            return

        added = 0
        for pos in broker_positions:
            try:
                deal_id = pos.get("deal_id")
                symbol = str(pos.get("symbol") or "").upper()
                direction = str(pos.get("direction") or "").upper()
                size = float(pos.get("size") or 0.0)
                entry = float(pos.get("entry_price") or 0.0)
                venue = str(pos.get("venue") or "capital").lower()
                if not deal_id or not symbol or size <= 0 or entry <= 0:
                    continue
                # Skip if already tracked (e.g. from persisted state)
                if any(getattr(p, 'deal_id', None) == deal_id for p in self.live_positions):
                    continue
                # Normalize direction vocabulary
                if direction in ("BUY", "LONG"):
                    direction = "LONG"
                elif direction in ("SELL", "SHORT"):
                    direction = "SHORT"
                else:
                    continue

                # We don't know the original TP/SL for broker-side positions
                # that pre-date this radar session; set a far-away synthetic
                # target so target_hit never fires, and let DTP manage exits.
                if direction == "LONG":
                    synthetic_target = entry * 1.5
                else:
                    synthetic_target = entry * 0.5

                pot = HoneyPot(
                    active=True,
                    deal_id=deal_id,
                    symbol=symbol,
                    sector=self.symbol_sectors.get(symbol, "commodity"),
                    direction=direction,
                    entry_price=entry,
                    target_price=synthetic_target,
                    size=size,
                    source="broker_reconciled",
                    opened_at=time.time(),
                    max_hold_seconds=self.honey_ladder.max_hold_seconds,
                )
                pot.venue = venue
                pot._live_path = "reconcile"
                self._attach_dtp(pot)
                self.live_positions.append(pot)
                added += 1
            except Exception as e:
                logger.warning(f"[RECONCILE] failed to adopt position {pos}: {e}")

        if added:
            logger.info(f"[RECONCILE] adopted {added} broker positions into radar tracking")
            self._save_state()

    def _reconcile_persisted_honey_pot(self):
        """Verify a persisted honey pot against the live positions API.

        Bug-hunt #2: without this, a restart with an open broker position
        saw honey_pot=None and opened a SECOND live trade.

        FAIL-CLOSED: when the positions API cannot be reached, the persisted
        pot is kept ACTIVE (no new live trade is allowed) rather than risk a
        duplicate. The pot is only cleared when the broker confirms the
        dealId is gone.
        """
        if self._honey_pot_reconciled:
            return
        self._honey_pot_reconciled = True

        data = getattr(self, '_persisted_honey_pot', None)
        self._persisted_honey_pot = None
        if not data or not data.get("deal_id"):
            return

        try:
            positions = self.capital_dual.get_live_positions()
        except Exception as e:
            logger.error(f"[HONEY POT] restart reconciliation FAILED (positions "
                         f"API error: {e}) — keeping persisted pot ACTIVE to "
                         f"prevent a duplicate live trade [fail-closed]")
            self._restore_honey_pot(data)
            return

        deal_id = data["deal_id"]
        still_open = any(
            isinstance(pos, dict) and
            pos.get("position", {}).get("dealId") == deal_id
            for pos in positions or []
        )
        if still_open:
            logger.info(f"[HONEY POT] restart reconciliation: dealId={deal_id} "
                        f"{data.get('symbol')} still open server-side — restored")
            self._restore_honey_pot(data)
        else:
            logger.warning(f"[HONEY POT] restart reconciliation: dealId={deal_id} "
                           f"NOT open server-side — clearing stale persisted pot "
                           f"(position already closed)")
            self.honey_ladder.honey_pot = None

    def _restore_honey_pot(self, data: dict):
        """Rebuild an active HoneyPot from persisted state."""
        self.honey_ladder.honey_pot = HoneyPot(
            active=True,
            deal_id=data.get("deal_id", ""),
            symbol=data.get("symbol", ""),
            sector=data.get("sector", ""),
            direction=data.get("direction", ""),
            entry_price=data.get("entry_price", 0.0),
            target_price=data.get("target_price", 0.0),
            size=data.get("size", 0.0),
            source=data.get("source", ""),
            opened_at=data.get("opened_at", time.time()),
            max_hold_seconds=data.get("max_hold_seconds", 600),
        )
        if data.get("audit_id"):
            self.honey_ladder.honey_pot._audit_id = data["audit_id"]
        # Keep the concurrent-positions list in sync with the restored pot.
        self.honey_ladder.honey_pot.venue = data.get("venue", "capital")
        self.live_positions.append(self.honey_ladder.honey_pot)
        self._attach_dtp(self.honey_ladder.honey_pot)
    
    def _try_auto_arm(self):
        """Auto-arm the hive if Honey Ladder has proven sources."""
        if self.state == SystemState.ARMED:
            return
        if self.state == SystemState.PANIC:
            return

        # Owner decree 2026-09-07: LIVE=1 means the hive is armed immediately.
        # The conscience/capital gates are the fail-closed authority; shadow
        # proof is optional when the owner has released the capital gate.
        if os.getenv("LIVE") == "1" or os.getenv("AUREON_FORCE_ARM") == "1":
            self.state = SystemState.ARMED
            self._save_state()
            logger.info("="*60)
            logger.info("[HIVE] OWNER-ARMED via LIVE=1 / AUREON_FORCE_ARM=1")
            logger.info("       ONE trade at a time. Penny profit. Live execution.")
            logger.info("="*60)
            return

        # Check if any source has reached adept+ (rung 3+)
        for source, record in self.honey_ladder.source_records.items():
            if record.current_ladder_rung >= 3 and record.phi_win_rate >= 0.60:
                self.state = SystemState.ARMED
                self._save_state()
                logger.info("="*60)
                logger.info("[HIVE] HONEY LADDER AUTO-ARMED")
                logger.info(f"       Source: {source} (rung {record.current_ladder_rung})")
                logger.info(f"       PHI Win Rate: {record.phi_win_rate:.1%}")
                logger.info("       ONE trade at a time. Penny profit. Shadow proves.")
                logger.info("="*60)
                return
    
    def panic(self):
        """PANIC mode — close everything, preserve capital.

        FAIL-CLOSED (bug-hunt #4): every close failure is logged loudly and
        surfaces — the bare `except: pass` that used to swallow KeyErrors
        (pos["dealId"] on the positions-API shape) and leave positions open
        is gone.
        """
        self.state = SystemState.PANIC
        self._save_state()
        logger.error("🚨 PANIC MODE — ALL TRADING HALTED 🚨")
        # Close all live positions
        positions = []
        try:
            positions = self.capital_dual.get_live_positions()
        except Exception as e:
            logger.error(f"🚨 PANIC: could not list live positions: {e}")
        for pos in positions or []:
            if not isinstance(pos, dict):
                logger.error(f"🚨 PANIC: malformed position entry: {pos!r}")
                continue
            deal_id = pos.get("position", {}).get("dealId")
            if not deal_id:
                logger.error(f"🚨 PANIC: position has no dealId: {pos!r}")
                continue
            try:
                result = self.capital_dual.close_live_position(deal_id)
                if isinstance(result, dict) and result.get("success"):
                    logger.info(f"Closed position: {deal_id}")
                else:
                    logger.error(f"🚨 PANIC: FAILED to close position {deal_id}: {result}")
            except Exception as e:
                logger.error(f"🚨 PANIC: error closing position {deal_id}: {e}")
    
    def scan(self):
        """Run a full scan cycle with Honey Ladder."""
        logger.info(f"--- HONEY LADDER SCAN @ {datetime.now(timezone.utc).isoformat()} ---")

        # One-time startup reconciliation of all broker-side live positions
        self._reconcile_existing_live_positions()

        # One-time restart reconciliation of a persisted honey pot (#2)
        self._reconcile_persisted_honey_pot()

        # Check honey pot status first (close if target hit)
        self._check_honey_pot()
        
        # Check demo shadows for validation (DUAL CAPITAL)
        self._check_demo_shadows()
        
        # ── HOMING CONTROLLER ──
        # Decide whether to concentrate fire on a single high-opportunity target
        # or scan the full watchlist. Price history is still fed for ALL symbols
        # below so the probability matrix keeps learning; signal generation is
        # restricted to the homing target when one is valid.
        self.homing_target = None
        homing_active = False
        if os.getenv("HOMING_ENABLED", "1").strip().lower() in ("1", "true", "yes"):
            try:
                self.homing_target = self.homing_controller.get_target()
                if self.homing_target and self.homing_target.is_valid():
                    homing_active = True
                    logger.info(f"[HOMING] locked on {self.homing_target.symbol} "
                                f"{self.homing_target.direction} "
                                f"score={self.homing_target.homing_score:.3f} "
                                f"venue={self.homing_target.venue}")
                else:
                    reason = (self.homing_target.blockers if self.homing_target else "no_target")
                    logger.info(f"[HOMING] no valid target ({reason}); scanning full watchlist")
            except Exception as e:
                logger.warning(f"[HOMING] controller error: {e}")
        
        # Try to auto-arm if ready
        self._try_auto_arm()
        
        # ── AUREON MOMENTUM BRIDGE ──
        # Feed prices to momentum scanner using price feed router (Binance/Kraken)
        try:
            from aureon_capital_momentum_bridge import CapitalMomentumScanner
            if not hasattr(self, '_momentum_scanner'):
                self._momentum_scanner = CapitalMomentumScanner(self.capital_live)
            
            # Feed current prices via price feed router (NOT direct Capital calls)
            self._momentum_scanner.feed_prices_from_capital(self.capital_live, self.symbol_keys)
            
            # Run momentum scan and write signals
            momentum_signals = self._momentum_scanner.scan_all()
            self._momentum_scanner.write_signals(momentum_signals)
        except Exception as e:
            logger.debug(f"Momentum bridge error: {e}")
        
        # Read unified hub signals (includes momentum bridge output)
        fused_signals = self._read_fused_signals()
        
        # Get sector heat
        sector_heat = self.honey_ladder.get_sector_heat()
        hot_sectors = [s for s, h in sector_heat.items() if h.sweet_spot]
        
        for symbol in self.symbol_keys:
            try:
                # Get price
                price = self._get_price(symbol)
                if price is None or not isinstance(price, (int, float)):
                    continue
                price = float(price)
                
                # Feed to scanner
                self.scanner.feed_price(symbol, price)

                # Record for the probability intelligence gate
                hist = self.price_history.setdefault(symbol, [])
                hist.append(price)
                if len(hist) > 200:
                    del hist[:-200]
                
                # Update shadows for this symbol
                _pre_status = {r.signal_id: r.status
                               for r in self.honey_ladder.shadow_runs
                               if r.symbol == symbol}
                self.honey_ladder.update_shadow(symbol, price)

                # 🧠 PROBABILITY LEARNING (price-based transitions):
                # OPEN→HIT is a real success, OPEN→MISS/EXPIRED is a real failure.
                # Without this the matrix only ever saw demo-upl successes and
                # drifted every source toward 100% accuracy.
                try:
                    from radar_probability_matrix import get_matrix as _pm
                    _mat = _pm()
                    for _r in self.honey_ladder.shadow_runs:
                        if _r.symbol != symbol or _pre_status.get(_r.signal_id) != 'OPEN':
                            continue
                        if _r.status == 'HIT':
                            _mat.record_outcome(source=_r.source, success=True)
                            logger.debug(f"[PROB] LEARNED(hit): {_r.source} {_r.symbol}")
                        elif _r.status in ('MISS', 'EXPIRED'):
                            _mat.record_outcome(source=_r.source, success=False)
                            logger.debug(f"[PROB] LEARNED(miss): {_r.source} {_r.symbol} {_r.status.lower()}")
                except Exception as _e:
                    logger.debug(f"[PROB] transition learning error: {_e}")

                # ── HOMING GATE ──
                # Keep feeding prices/shadows for every symbol so the matrix
                # learns, but only generate signals/trades for the locked target.
                if homing_active and symbol != self.homing_target.symbol:
                    continue

                # Calculate metrics
                volatility = self.scanner.calculate_volatility(symbol)
                money_flow = self.scanner.money_flow_score(symbol)
                breakout, direction, strength = self.scanner.detect_breakout(symbol)
                
                sector = self.symbol_sectors.get(symbol, "commodity")
                
                # CHECK SIGNAL SOURCES
                source_confidence = {}
                for sig_symbol, sig in fused_signals.items():
                    if sig_symbol == symbol:
                        src = sig.get('source', 'unknown')
                        # SIM-SEVER-B: bridge stdout signals carry confidence
                        # None (never invented) — treat None as low priority (0.0)
                        raw_conf = sig.get('confidence')
                        conf = raw_conf if isinstance(raw_conf, (int, float)) else 0.0
                        source_confidence[src] = conf
                        
                        # If source is strong, boost breakout
                        if conf > 0.6:
                            breakout = True
                            direction = sig.get('direction', direction)
                            strength = max(strength, conf)
                            logger.info(f"[SIGNAL] {src}: {symbol} {direction} conf={conf:.2f}")
                
                # Generate signal when:
                #   - our own scanner detects a breakout, OR
                #   - a fused source (unified hub / volatility scanner) is confident.
                # Owner decree 2026-09-07: trust high-confidence external signals
                # (conf >= 0.30) so Capital.com targets promoted by the volatility
                # scanner can trade immediately.
                fused_conf = max(source_confidence.values()) if source_confidence else 0.0
                if breakout or fused_conf >= 0.30:
                    if fused_conf >= 0.30:
                        # Use direction/strength from the strongest fused signal
                        for sig_symbol, sig in fused_signals.items():
                            if sig_symbol == symbol and sig.get('confidence', 0) == fused_conf:
                                direction = sig.get('direction', direction)
                                strength = max(strength, fused_conf)
                                breakout = True
                                break
                    
                    # ── PLAY-BOARD OPTIMIZER ──
                    # Select the dynamic strategy play for this symbol and moment.
                    # The plan carries target style, DTP thresholds, hold time,
                    # and sizing guidance. It is passed downstream to signal,
                    # sizing, and DTP construction.
                    try:
                        self.current_play_plan = self.play_board.build_plan(
                            symbol,
                            price_history=self.price_history.get(symbol, []),
                            signal_confidence=fused_conf,
                            direction=direction,
                            volatility=volatility,
                            money_flow=money_flow,
                        )
                        exec_plan = self.current_play_plan.get("execution") or {}
                        logger.info(f"[PLAY_BOARD] {symbol} {exec_plan.get('action')} "
                                    f"archetype={exec_plan.get('primary_archetype')} "
                                    f"style={exec_plan.get('target_style')} "
                                    f"dtp=£{exec_plan.get('dtp_activation_gbp')} "
                                    f"hold={exec_plan.get('max_hold_minutes')}m")
                    except Exception as e:
                        logger.warning(f"[PLAY_BOARD] optimizer error for {symbol}: {e}")
                        self.current_play_plan = None
                    
                    signal = self._generate_signal(symbol, price, direction, strength, volatility, money_flow, play_plan=self.current_play_plan)
                    
                    # Determine best source for this signal
                    best_source = "scanner"
                    best_conf = strength
                    for src, conf in source_confidence.items():
                        if conf > best_conf:
                            best_source = src
                            best_conf = conf
                    
                    # 🧠 PROBABILITY INTELLIGENCE GATE
                    # Evaluate signal through probability matrix before spending demo trade
                    try:
                        from radar_probability_matrix import evaluate_signal, should_trade
                        
                        # Build price history for volatility/momentum analysis
                        price_history = self.price_history.get(symbol, [price])
                        
                        intel = evaluate_signal(
                            symbol=symbol,
                            direction=direction,
                            confidence=best_conf,  # best calibrated 0..1 input
                            source=best_source,     # (max of breakout strength
                            price_history=price_history,  # and fused-source conf)
                            sector=sector
                        )
                        
                        # Log probability analysis
                        from radar_probability_matrix import get_matrix
                        explanation = get_matrix().explain(intel, symbol)
                        for line in explanation.split('\n'):
                            logger.info(f"[PROB] {line}")
                        
                        # Gate: only proceed if probability passes threshold
                        # Owner decree 2026-09-07: lower gate to capture micro-moves
                        # on Capital.com with the 1p/1c profit target.
                        if not should_trade(intel, min_threshold=self._probability_threshold()):
                            logger.warning(f"[PROB] BLOCKED: {symbol} {direction} — "
                                         f"adjusted_prob={intel.adjusted_probability:.1%}, "
                                         f"action={intel.action}, "
                                         f"risks={intel.risk_flags}")
                            continue  # Skip this signal — probability too low
                        
                        logger.info(f"[PROB] APPROVED: {symbol} {direction} — "
                                   f"adjusted_prob={intel.adjusted_probability:.1%} ✅")
                        
                    except Exception as e:
                        # FAIL-CLOSED: probability matrix error blocks the signal
                        logger.error(f"[PROB] BLOCKED: probability evaluation error: {e} — "
                                     f"{symbol} {direction} signal blocked [fail-closed]")
                        continue  # Skip this signal — probability could not be verified
                    
                    # Calculate micro-scalp target (1 tick/pip)
                    micro_target = self.capital_dual.calculate_micro_tp(
                        symbol=symbol,
                        direction=direction,
                        entry_price=price
                    )

                    # ── STRATEGIC / BUSINESS INTELLIGENCE SWEEP ──
                    # Porter's 5 Forces, SWOT, Fourier spectrum, cross-asset
                    # correlation, capital allocation, and QGITA truth gate.
                    try:
                        stop_for_analysis = self._compute_stop_level(symbol, direction, price)
                        if stop_for_analysis is None:
                            stop_for_analysis = price * (0.99 if direction.upper() in ("LONG", "BUY") else 1.01)
                        live_balance = self.capital_dual.get_live_balance()
                        if not live_balance or live_balance <= 0:
                            logger.warning(f"[STI] {symbol} {direction}: live balance unavailable — skipping QGITA filter (no fabricated balance)")
                            sti_report = None
                        else:
                            sti_report = _sti.analyze_trade(
                                symbol=symbol,
                                direction=direction,
                                entry=price,
                                stop=stop_for_analysis,
                                tp=micro_target,
                                balance_gbp=live_balance,
                            )
                        if sti_report:
                            qgita_verdict = sti_report.get("qgita_sweep", {}).get("verdict")
                            logger.info(f"[STI] {symbol} {direction} QGITA={qgita_verdict} "
                                       f"sharpe={sti_report.get('fourier_spectrum', {}).get('dominant_period_bars')}")
                            # Fail-closed discernment: QGITA HOLD/CONTRADICTED skips the signal.
                            if qgita_verdict in ("HOLD", "CONTRADICTED"):
                                logger.warning(f"[STI] {symbol} {direction} skipped by QGITA "
                                               f"verdict={qgita_verdict}")
                                continue
                    except Exception as e:
                        logger.debug(f"[STI] strategic analysis error for {symbol}: {e}")
                    
                    # Add shadow to ladder with micro-scalp target
                    self.honey_ladder.add_shadow(
                        symbol=symbol,
                        sector=sector,
                        direction=direction,
                        entry_price=price,
                        source=best_source,
                        target_price=micro_target
                    )

                    # Stash the matrix-approved admission confidence on the run
                    # so _execute_honey_pot can re-validate at execution time.
                    if self.honey_ladder.shadow_runs:
                        self.honey_ladder.shadow_runs[-1]._matrix_conf = best_conf
                    
                    # 🚦 EXPECTANCY GATE (Gary's decree): every demo order must
                    # clear 1.25x the venue's real round-trip cost on the
                    # confidence-scaled expected move — same contract as the
                    # hub shadow arm. Confidence is the matrix's calibrated
                    # adjusted_probability (0..1), never a raw scanner score.
                    # Refusal skips the demo order only; the shadow stays for
                    # price-based learning. Fail-closed on any gate error.
                    _pre_dir = direction.upper()
                    if _pre_dir == "LONG":
                        _pre_dir = "BUY"
                    elif _pre_dir == "SHORT":
                        _pre_dir = "SELL"
                    _gv = self._expectancy_gate_verdict(
                        symbol, _pre_dir, 1.0, price,
                        getattr(intel, "adjusted_probability", 0.0),
                        f"demo {symbol} {direction}")
                    _gate_ok = bool(_gv.get("allowed"))

                    # Place DEMO trade for validation (DUAL CAPITAL)
                    if _gate_ok and symbol not in ["BTCUSD", "ETHUSD"]:
                        try:
                            logger.info(f"[DEMO] Attempting demo trade for {symbol}")
                            cap_direction = direction.upper()
                            if cap_direction == "LONG":
                                cap_direction = "BUY"
                            elif cap_direction == "SHORT":
                                cap_direction = "SELL"
                            
                            # Capital.com CFD minimum size (will be overridden
                            # by dynamic live sizing when LIVE=1 is active).
                            demo_size = 1.0
                            profit_distance = price * 0.0005
                            if direction == "LONG":
                                profit_level = round(price + profit_distance, 2)
                            else:
                                profit_level = round(price - profit_distance, 2)
                            
                            # OVERRIDE with micro-scalp: 1 tick/pip profit
                            profit_level = self.capital_dual.calculate_micro_tp(
                                symbol=symbol,
                                direction=direction,
                                entry_price=price
                            )
                            # Owner decree 2026-09-06: demo TP also honors the
                            # capture floor (>= 1.0% gain), clamped upward.
                            profit_level = self._floor_clamp_tp(
                                direction, price, profit_level)
                            
                            logger.info(f"[DEMO] Micro-scalp TP: {symbol} {direction} "
                                       f"entry={price} TP={profit_level} (1 tick)")

                            # Owner decree 2026-09-07: when LIVE=1 and ARMED,
                            # route real trades through the multi-venue router.
                            # Demo/shadow path stays on Capital.com demo.
                            is_live_path = (os.getenv("LIVE") == "1" and self.state == SystemState.ARMED)
                            if is_live_path:
                                # Mandatory broker-side stop: use the same fail-closed
                                # computation as the honey-pot path so it meets Capital's
                                # minimum distance requirements (router passes it through).
                                stop_level = self._compute_stop_level(symbol, direction, price)
                                if stop_level is None:
                                    logger.error(f"[LIVE] Stop computation failed for {symbol} — "
                                                 f"refusing live order [fail-closed]")
                                    continue
                                # Dynamic, account-aware sizing. Skip the symbol if the
                                # live account cannot afford even the minimum lot.
                                live_size = self._compute_live_size(symbol, price, stop_level)
                                if live_size is None:
                                    logger.warning(f"[LIVE] {symbol} skipped: account cannot "
                                                   f"afford a viable position [fail-closed]")
                                    continue
                                # Aggregate margin guard: the router also enforces a
                                # 50% total-account cap; this log gives visibility.
                                exposure = self.router.aggregate_exposure()
                                logger.info(f"[LIVE] Aggregate exposure before order: "
                                           f"{exposure['position_exposure']:.2f}/"
                                           f"{exposure['limit']:.2f} "
                                           f"({exposure['utilization_pct']:.1f}% utilized)")
                                logger.info(f"[LIVE] Routing order: {symbol} {cap_direction} "
                                           f"size={live_size} entry={price} "
                                           f"TP={profit_level} SL={stop_level}")
                                result = self.router.place_order(
                                    symbol=symbol,
                                    direction=cap_direction,
                                    size=live_size,
                                    stop_level=stop_level,
                                    profit_level=profit_level
                                )
                            else:
                                result = self.capital_dual.place_demo_order(
                                    symbol=symbol,
                                    direction=cap_direction,
                                    size=demo_size,
                                    profit_level=profit_level
                                )
                            
                            deal_id = result.get("dealId")
                            is_accepted = (
                                deal_id is not None and deal_id not in ("", "unknown")
                                and not result.get("error")
                            )
                            if is_accepted:
                                account = result.get("account", "live" if is_live_path else "demo")
                                is_live_account = (account == "live" or account.endswith("_live"))
                                if is_live_path and is_live_account:
                                    self.live_trades_today += 1
                                    try:
                                        with open(LIVE_LOG, "a") as f:
                                            f.write(json.dumps({
                                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                                "symbol": symbol,
                                                "direction": cap_direction,
                                                "size": result.get("size"),
                                                "dealId": deal_id,
                                                "venue": result.get("venue"),
                                                "entry": price,
                                                "tp": profit_level,
                                                "sl": stop_level if 'stop_level' in locals() else None,
                                            }) + "\n")
                                    except Exception:
                                        pass
                                    # Track the new live position alongside any others.
                                    pot = HoneyPot(
                                        active=True,
                                        deal_id=deal_id,
                                        symbol=symbol,
                                        sector=sector,
                                        direction=direction,
                                        entry_price=price,
                                        target_price=profit_level,
                                        size=result.get("size", live_size),
                                        source="scanner_live",
                                        opened_at=time.time(),
                                        max_hold_seconds=self._max_hold_seconds(symbol),
                                    )
                                    pot.venue = result.get("venue", "capital")
                                    pot._live_path = "scan"
                                    self.live_positions.append(pot)
                                    self._attach_dtp(pot)
                                    self.honey_ladder.honey_pot = pot  # backward-compat status
                                    logger.info(f"[LIVE] Trade accepted: {symbol} "
                                               f"dealId={deal_id} venue={pot.venue} "
                                               f"size={result.get('size')}")
                                else:
                                    # Store demo dealId on the shadow we just added
                                    if self.honey_ladder.shadow_runs:
                                        shadow = self.honey_ladder.shadow_runs[-1]
                                        shadow._demo_deal_id = deal_id
                                    logger.info(f"[DEMO] Shadow trade placed: {symbol} "
                                               f"dealId={deal_id}")
                            else:
                                label = "LIVE" if is_live_path else "DEMO"
                                logger.warning(f"[{label}] Failed to place order for {symbol}: "
                                              f"{result.get('error', 'unknown error')}")
                        except Exception as e:
                            logger.info(f"[DEMO] Error placing shadow for {symbol}: {e}")
                    
                    logger.info(f"[SHADOW] Added {symbol} {direction} to ladder "
                               f"(source: {best_source}, sector: {sector})")
                    
            except Exception as e:
                logger.error(f"Scan error for {symbol}: {e}")
        
        # Try to promote best shadow to honey pot
        self._promote_to_honey_pot()
    
    # Signal-source priority, highest first (bug-hunt #6: the old code's
    # comments claimed bridge > hub > ollama-fill-gaps but then let
    # planetary/crypto/stock silently OVERRIDE earlier sources). First source
    # to claim a symbol wins; later sources only fill gaps.
    _FUSED_SIGNAL_SOURCES = [
        ("aureon_bridge_signals.jsonl", "AUREON BRIDGE"),
        ("fused_signals.jsonl", "UNIFIED HUB"),
        ("ollama_signals.jsonl", "OLLAMA"),
        ("planetary_signals.jsonl", "PLANETARY"),
        ("crypto_signals.jsonl", "CRYPTO"),
        ("stock_signals.jsonl", "STOCK"),
    ]

    def _fused_signal_ttl_sec(self) -> float:
        """Max signal age accepted from signal files (bug-hunt #6).

        Default 5 minutes; configurable via RADAR_FUSED_SIGNAL_TTL_SEC.
        Unparseable values fall back to the default (never open-ended).
        """
        try:
            ttl = float(os.getenv("RADAR_FUSED_SIGNAL_TTL_SEC", "300"))
            return ttl if ttl > 0 else 300.0
        except Exception:
            return 300.0

    def _signal_is_fresh(self, sig: dict) -> bool:
        """TTL-filter a signal. Missing/unparseable timestamp → stale
        (fail-closed: any-age signals are never accepted)."""
        ts = sig.get("timestamp")
        if not ts:
            return False
        try:
            ts_norm = str(ts).replace("Z", "+00:00")
            sig_time = datetime.fromisoformat(ts_norm).timestamp()
        except Exception:
            return False
        age = time.time() - sig_time
        if age < 0:
            age = 0  # small clock skew is fine
        return age <= self._fused_signal_ttl_sec()

    def _read_fused_signals(self) -> Dict[str, dict]:
        """Read latest fused signals from unified hub AND Aureon OS bridge.

        Bug-hunt #6: signals are TTL-filtered (default >5 min dropped) and
        priority is explicit — see _FUSED_SIGNAL_SOURCES. Higher-priority
        sources claim a symbol first; lower-priority sources fill gaps only.
        """
        signals = {}
        ttl = self._fused_signal_ttl_sec()

        for filename, label in self._FUSED_SIGNAL_SOURCES:
            sig_file = RADAR_DIR / filename
            if not sig_file.exists():
                continue
            try:
                with open(sig_file) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            sig = json.loads(line)
                        except Exception:
                            continue
                        sym = sig.get('symbol', '')
                        if not sym or sym in signals:
                            continue
                        if not self._signal_is_fresh(sig):
                            logger.debug(f"[{label}] dropped stale/no-ts signal: {sym}")
                            continue
                        signals[sym] = sig
                        conf = sig.get('confidence', 0)
                        try:
                            conf_s = f"{conf:.2f}"
                        except Exception:
                            conf_s = str(conf)
                        logger.info(f"[{label}] {sym} {sig.get('direction')} "
                                    f"conf={conf_s}")
            except Exception as e:
                logger.debug(f"Signal file read error ({filename}): {e}")

        if signals:
            logger.info(f"[SIGNALS] {len(signals)} fresh fused signals (TTL {ttl:.0f}s)")
        return signals
    
    def _get_price(self, symbol: str, max_age_sec: Optional[float] = None) -> Optional[float]:
        """Get current price from the live feed only — NO synthetic fallback.

        Bug-hunt MEDIUM: the old hardcoded hash()-noise "prices" could anchor
        stops and position sizing when the feed was down. Now a feed failure
        simply yields None (callers skip/refuse).

        When max_age_sec is given (live execution path), a quote older than
        that is treated as unavailable — stale data never executes live.
        """
        try:
            from aureon_price_feed import get_price, _price_cache
            price = get_price(symbol, capital_connector=self.capital_live, prefer_capital=True)
            if not price or price <= 0:
                return None
            if max_age_sec is not None:
                cached = _price_cache.get(symbol)
                age = (time.time() - cached["time"]) if cached else float("inf")
                if age > max_age_sec:
                    logger.error(f"[PRICE] {symbol} quote stale "
                                 f"({age:.0f}s > {max_age_sec:.0f}s) — treating as "
                                 f"unavailable for live execution [fail-closed]")
                    return None
            return float(price)
        except Exception as e:
            logger.debug(f"Price feed error: {e}")
            return None
    
    def _generate_signal(self, symbol: str, price: float, direction: str,
                         strength: float, volatility: float, money_flow: float,
                         play_plan: Optional[Dict[str, Any]] = None) -> MarketSignal:
        """Generate a trading signal -- NO STOP LOSS, only TP. Ride the harmonic wave.

        Play-board optimizer can request a larger profit target for momentum
        or swing plays while keeping micro-scalps tight.
        """
        exec_plan = (play_plan or {}).get("execution") or {}
        target_style = exec_plan.get("target_style", "micro")

        if target_style == "momentum":
            profit_pct = 0.005   # 0.5%
        elif target_style == "swing":
            profit_pct = 0.010   # 1.0%
        else:  # micro
            profit_pct = 0.0005  # 0.05%

        profit_distance = price * profit_pct
        profit_distance = max(profit_distance, 0.04)
        
        if direction == "LONG":
            target = price + profit_distance
        else:
            target = price - profit_distance
        
        # SIM-SEVER-B: no fabricated stop. The old dummy stops (price*0.5 /
        # price*2.0 constants) are gone — consumers that need a stop already
        # require a real broker-side stop_level computed from live quotes
        # (_compute_stop_level, fail-closed). Signal records carry
        # stop_loss=None rather than a constant literal.
        stop = None
        
        # Phi-resonance score
        phi_resonance = (strength * PHI + money_flow * (1/PHI)) / (PHI + 1/PHI)
        
        signal = MarketSignal(
            timestamp=datetime.now(timezone.utc).isoformat(),
            symbol=symbol,
            direction=direction,
            strength=strength,
            entry_price=price,
            target_price=target,
            stop_loss=stop,
            confidence=max(0.0, min(strength * phi_resonance * 1.2, 1.0)),  # 0..1; a probability field must never go negative
            source="AureonPhiRadar",
            phi_resonance=phi_resonance,
            volatility_reading=volatility,
            money_flow_score=money_flow
        )
        
        return signal
    
    def _promote_to_honey_pot(self):
        """Check if any shadow is ready to graduate to a live position.

        Owner decree 2026-09-07: the one-trade-at-a-time honey-pot gate is
        relaxed. Multiple concurrent live positions are allowed, subject to the
        aggregate 50% account-value margin cap enforced by the router.
        HoneyLadder is still used for shadow tracking and graduation.
        """
        if self.state != SystemState.ARMED:
            return

        # Find graduation candidate (no longer blocked by an active honey pot)
        candidate = self.honey_ladder.get_graduation_candidate()
        if not candidate:
            return

        # Execute live trade through the multi-venue router
        self._execute_honey_pot(candidate)
    
    def _calculate_position_size(self, symbol: str, price: float, rung: int = 1) -> float:
        """Calculate position size based on account balance and ladder rung.
        
        Strategy: Deploy 85% of available balance. Higher rung = bigger size.
        One trade at a time = full capital rotation.
        """
        try:
            balance = self.capital_live.get_account_balance()
            if not isinstance(balance, (int, float)) or balance < 10:
                logger.warning(f"[SIZE] balance unavailable/insufficient ({balance}) — refusing size [fail-closed]")
                return 0.0
            
            # Rung multipliers - bigger size as source proves itself
            rung_multipliers = {
                1: 1.0,   # Initiate: base size
                2: 1.5,   # Adept: 1.5x
                3: 2.5,   # Scholar: 2.5x
                4: 4.0,   # Sage: 4x
                5: 6.0,   # Master: 6x
            }
            multiplier = rung_multipliers.get(rung, 1.0)
            
            # Play-board / homing size boost
            size_mult = self._size_boost(symbol)
            
            # Deploy 85% of balance (leave 15% buffer for margin safety)
            deploy_capital = balance * 0.85 * multiplier * size_mult
            
            # Category-specific leverage approximation for Capital.com CFDs
            # These are rough estimates - Capital.com handles actual margin
            category_leverage = {
                "forex": 30,     # ~30:1 for major forex
                "commodity": 10, # ~10:1 for gold/oil
                "tech": 5,       # ~5:1 for indices/stocks
                "crypto": 2,     # ~2:1 for crypto
            }
            sector = self.symbol_sectors.get(symbol, "commodity")
            leverage = category_leverage.get(sector, 5)
            
            # Calculate raw size: (deploy_capital * leverage) / price
            # For forex, price is quoted per unit so we need to adjust
            if sector == "forex":
                # Forex: size in units. 1 unit at price = price in quote currency
                # With GBP account, need to account for cross rates
                raw_size = (deploy_capital * leverage) / (price * 1000)
            else:
                raw_size = (deploy_capital * leverage) / price
            
            # Round to 2 decimal places (Capital.com standard)
            size = round(raw_size, 2)
            
            # Minimum size enforcement (broker lot size)
            size = max(size, 0.01)
            
            # Hard cap: never risk more than balance allows
            notional = size * price / leverage
            if notional > balance * 0.9:
                size = round((balance * 0.9 * leverage) / price, 2)
            
            logger.info(f"[SIZE] Balance: £{balance:.2f} | Rung: {rung} | "
                       f"Multiplier: {multiplier}x | Leverage: {leverage}:1 | "
                       f"Size: {size} | Deploy: £{notional:.2f}")
            
            return max(size, 0.0)
            
        except Exception as e:
            logger.error(f"Size calc error: {e}")
            return 0.0

    # ── FAIL-CLOSED SAFETY GATES (owner decree 2026-09-04) ──

    def _emit_gate_refused_event(self, payload: dict):
        """Best-effort trading.gate_refused event via aureon_fusion.events."""
        try:
            if str(WORKSPACE) not in sys.path:
                sys.path.insert(0, str(WORKSPACE))
            from aureon_fusion import events
            events.publish_event("trading", "trading.gate_refused", payload, priority=7)
        except Exception:
            pass  # event spine unavailable — refusal already logged

    def _live_trading_gate_allowed(self, context: str) -> bool:
        """Belt-and-braces capability gate (connector re-checks too).

        Fail-closed: any gate-module error or allowed!=True → refuse.
        """
        gate_key = "trading_execution:execute_live_trades"
        try:
            if str(WORKSPACE) not in sys.path:
                sys.path.insert(0, str(WORKSPACE))
            from aureon_fusion import capability_gate
            verdict = capability_gate.check(gate_key)
        except Exception as e:
            logger.error(f"[GATE] capability_gate error ({e}) — REFUSING live "
                         f"order ({context}) [fail-closed]")
            self._emit_gate_refused_event({
                "gate": gate_key, "verdict": "ERROR", "allowed": False,
                "reason": f"capability_gate check raised: {e}", "context": context})
            return False

        if not verdict.get("allowed"):
            logger.warning(f"[GATE] REFUSED live order ({context}): "
                           f"verdict={verdict.get('verdict')} reason={verdict.get('reason')}")
            self._emit_gate_refused_event({
                "gate": gate_key, "verdict": verdict.get("verdict"),
                "allowed": False, "level": verdict.get("level"),
                "reason": verdict.get("reason"), "context": context})
            return False
        return True

    def _daily_live_cap_reached(self) -> bool:
        """Enforce max live executions per UTC day (env
        RADAR_MAX_LIVE_TRADES_PER_DAY, default 3). Fail-closed on an
        unparseable value. Counter resets on UTC date change."""
        raw = os.getenv("RADAR_MAX_LIVE_TRADES_PER_DAY", "3")
        try:
            max_trades = int(str(raw).strip())
            if max_trades < 0:
                raise ValueError("negative cap")
        except Exception:
            logger.error(f"[CAP] Unparseable RADAR_MAX_LIVE_TRADES_PER_DAY={raw!r} — "
                         f"REFUSING live order [fail-closed]")
            return True

        today = datetime.now(timezone.utc).date().isoformat()
        if self._live_trades_date != today:
            self.live_trades_today = 0
            self._live_trades_date = today

        if self.live_trades_today >= max_trades:
            logger.warning(f"[CAP] REFUSED live order: daily cap reached "
                           f"({self.live_trades_today}/{max_trades} live executions today, UTC)")
            return True
        return False

    def _notional_cap_exceeded(self, symbol: str, size: float, price: float,
                               equity) -> bool:
        """Refuse orders whose notional exceeds RADAR_MAX_NOTIONAL_PCT
        (default 150) percent of live equity. Fail-closed when the equity
        cannot be fetched or the env value is unparseable."""
        raw = os.getenv("RADAR_MAX_NOTIONAL_PCT", "150")
        try:
            max_pct = float(str(raw).strip())
            if max_pct <= 0:
                raise ValueError("non-positive cap")
        except Exception:
            logger.error(f"[NOTIONAL] Unparseable RADAR_MAX_NOTIONAL_PCT={raw!r} — "
                         f"REFUSING live order [fail-closed]")
            return True

        if not isinstance(equity, (int, float)) or equity <= 0:
            logger.error(f"[NOTIONAL] Cannot fetch live equity (got {equity!r}) — "
                         f"REFUSING live order for {symbol} [fail-closed]")
            return True

        # Forex CFDs on Capital.com are sized in units of 1000
        multiplier = 1000.0 if self.symbol_sectors.get(symbol) == "forex" else 1.0
        notional = size * price * multiplier
        limit = equity * max_pct / 100.0
        if notional > limit:
            logger.warning(f"[NOTIONAL] REFUSED live order {symbol}: notional "
                           f"£{notional:.2f} exceeds {max_pct}% of live equity "
                           f"£{equity:.2f} (limit £{limit:.2f})")
            return True
        return False

    def _compute_live_size(self, symbol: str, entry_price: float,
                           stop_level: float) -> Optional[float]:
        """Capital-aware position sizing: fit both margin and risk inside the
        live account. Returns None when even the minimum lot cannot be afforded
        or the risk would exceed the daily risk budget."""
        try:
            # Venue-aware balance: US equities route to Alpaca, so size against
            # Alpaca buying power rather than Capital.com balance.
            classification = _classify_symbol(symbol)
            asset_class = classification.get("asset_class", "")
            if asset_class == "us_equity" and hasattr(self, "router"):
                balance_usd = self.router.venue_balance("alpaca", "USD")
                gbpusd = self._get_price("GBPUSD") or 1.35
                balance_gbp = balance_usd / gbpusd
            else:
                balance_gbp = self.capital_dual.get_live_balance()
                gbpusd = self._get_price("GBPUSD") or 1.35

            if not isinstance(balance_gbp, (int, float)) or balance_gbp < 1:
                logger.error(f"[SIZE] Live balance unavailable ({balance_gbp!r}) — "
                             f"refusing {symbol} [fail-closed]")
                return None

            # FX rates to move between account currency (GBP) and the
            # instrument's quote currency.
            usdjpy = self._get_price("USDJPY") or 150.0

            category = self.capital_dual._get_symbol_category(symbol)
            rules = self.capital_dual._get_dealing_rules(symbol) or {}
            currency = rules.get("currency") or "USD"
            margin_factor = rules.get("marginFactor")
            min_deal_size = rules.get("minDealSize")
            size_increment = rules.get("minSizeIncrement")

            if margin_factor is None:
                margin_factor = {
                    "forex": 3.333, "stock": 20.0, "commodity": 10.0,
                    "index": 5.0, "crypto": 50.0,
                }.get(category, 10.0)
            # US single stocks now route to Alpaca (Reg-T ~50% margin) when live
            # trading is enabled. Use the more conservative Alpaca margin so the
            # aggregate exposure cap does not reject the order after sizing.
            if symbol.upper() in ("AAPL", "TSLA", "NVDA") and os.getenv("APCA_LIVE") == "true":
                margin_factor = 50.0
            if min_deal_size is None:
                min_deal_size = {"US100": 0.001}.get(symbol.upper(), 0.01)
            if size_increment is None:
                size_increment = min_deal_size
            size_increment = max(float(size_increment), float(min_deal_size))
            margin_factor_dec = float(margin_factor) / 100.0

            # Approximate units per lot. Capital's `size` field is in lots.
            lot_units = {
                "forex": 100000.0, "commodity": 1000.0,
                "stock": 1.0, "index": 1.0, "crypto": 1.0,
            }.get(category, 1.0)

            # Convert live balance into the instrument's quote currency.
            if currency == "GBP":
                balance_cur = balance_gbp
            elif currency == "JPY":
                balance_cur = balance_gbp * gbpusd * usdjpy
            else:  # USD and default
                balance_cur = balance_gbp * gbpusd

            # Keep margin usage <= 30% of available balance.
            margin_budget = balance_cur * 0.30
            notional_per_lot = entry_price * lot_units
            if notional_per_lot <= 0 or margin_factor_dec <= 0:
                return None
            max_size_by_margin = margin_budget / (notional_per_lot * margin_factor_dec)

            # Keep estimated risk <= 10% of available balance.
            price_distance = abs(entry_price - stop_level)
            if price_distance <= 0:
                price_distance = entry_price * 0.001
            risk_per_lot = price_distance * lot_units
            risk_budget = balance_cur * 0.10
            max_size_by_risk = risk_budget / risk_per_lot if risk_per_lot > 0 else float("inf")

            size = min(max_size_by_margin, max_size_by_risk)

            # Homing target / play-board selected play gets concentrated allocation.
            size_mult = self._size_boost(symbol)
            if size_mult > 1.0:
                size = size * size_mult
                logger.info(f"[SIZE] {symbol} size boost {size_mult}x "
                            f"(raw={size / size_mult:.4f})")

            size = max(size, float(min_deal_size))
            # Round down to the instrument's size increment.
            size = math.floor(size / size_increment) * size_increment

            if size < float(min_deal_size):
                logger.warning(f"[SIZE] {symbol}: even minimum lot {min_deal_size} "
                               f"exceeds account capacity (margin_size={max_size_by_margin:.4f}, "
                               f"risk_size={max_size_by_risk:.4f}) — skipping")
                return None

            logger.info(f"[SIZE] {symbol} size={size:.4f} lots "
                        f"(margin_limit={max_size_by_margin:.4f}, "
                        f"risk_limit={max_size_by_risk:.4f}, balance=£{balance_gbp:.2f})")
            return size
        except Exception as e:
            logger.error(f"[SIZE] sizing failed for {symbol}: {e} — refusing [fail-closed]")
            return None

    def _compute_stop_level(self, symbol: str, direction: str,
                            entry_price: float) -> Optional[float]:
        """Mandatory broker-side stop loss: RADAR_STOP_LOSS_PCT (default 1.5)
        percent adverse from entry, raised to Capital.com's minimum distance
        for the instrument. Returns None (→ refuse) on any failure."""
        try:
            raw = os.getenv("RADAR_STOP_LOSS_PCT", "1.5")
            sl_pct = float(str(raw).strip())
            if sl_pct <= 0:
                raise ValueError("non-positive stop pct")
        except Exception:
            logger.error(f"[STOP] Unparseable RADAR_STOP_LOSS_PCT — REFUSING "
                         f"live order for {symbol} [fail-closed]")
            return None

        try:
            import math
            distance = entry_price * sl_pct / 100.0
            min_distance = self.capital_dual.get_minimum_stop_distance(symbol, entry_price)
            distance = max(distance, min_distance)
            is_long = direction.upper() in ("LONG", "BUY")
            raw_stop = entry_price - distance if is_long else entry_price + distance
            if raw_stop <= 0:
                raise ValueError("non-positive stop level")
            # Round away from entry so rounding never pushes the stop inside the
            # broker's minimum-distance envelope.
            factor = 10 ** 4
            if is_long:
                stop = math.floor(raw_stop * factor) / factor
            else:
                stop = math.ceil(raw_stop * factor) / factor
            return stop
        except Exception as e:
            logger.error(f"[STOP] Stop loss computation failed for {symbol}: {e} — "
                         f"REFUSING live order [fail-closed]")
            return None

    # ── OWNER CAPTURE FLOOR (Gary Leckey, 2026-09-06: ≥1.0% gain per trade) ──

    _floor_mod = None
    _floor_attempted = False

    def _load_capture_floor_mod(self):
        """Load capture_floor.py by path, once (same bootstrap as the gate).

        None => floor inert; every clamp then returns the target unchanged.
        """
        if self._floor_attempted:
            return self._floor_mod
        self._floor_attempted = True
        try:
            import importlib.util
            path = RADAR_DIR / "exchange_adapters" / "capture_floor.py"
            spec = importlib.util.spec_from_file_location(
                "aureon_capture_floor_phi", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            self._floor_mod = mod
        except Exception as e:
            logger.debug(f"capture_floor unavailable ({e}) — floor inert")
        return self._floor_mod

    def _floor_clamp_tp(self, direction: str, entry_price: float,
                        target_price: float) -> float:
        """Clamp a take-profit target UPWARD to the owner capture floor.

        Read at call time: a missing/corrupt state/capture_floor.json (or a
        loader error) means the floor is absent and the target is returned
        unchanged — prior behavior, never a crash on the order path.
        """
        mod = self._load_capture_floor_mod()
        if mod is None:
            return target_price
        try:
            floor = mod.load_capture_floor()
            if floor is None:
                return target_price
            clamped = mod.apply_floor_to_target(
                direction, entry_price, target_price, floor)
            if clamped != target_price:
                logger.info(f"[FLOOR] TP raised to capture floor "
                            f"{floor * 100:.1f}%: {direction} entry={entry_price} "
                            f"{target_price} -> {clamped} (owner decree 2026-09-06)")
            return clamped
        except Exception as e:
            logger.debug(f"capture floor clamp failed ({e}) — target unchanged")
            return target_price

    # ── EXPECTANCY GATE (Gary's decree, single enforcement point) ──

    _GATE_VENUE = "capital"  # phi-radar executes exclusively on Capital.com

    def _expectancy_gate_verdict(self, symbol: str, side: str, qty: float,
                                 price: float, confidence: float,
                                 context: str) -> Dict[str, Any]:
        """Fee-aware expectancy check via exchange_adapters/expectancy_gate.py
        (loaded by path, same bootstrap pattern as unified_hub).

        The gate's contract: expected_move (confidence × stop_pct) must clear
        1.25× the venue's real round-trip cost; an unmapped venue is a
        fail-closed refusal, and a gate error here is ALSO a refusal — an
        order whose edge cannot be verified never fires.

        `confidence` must be a calibrated 0..1 probability: callers pass the
        matrix's adjusted_probability (demo path) or the source's measured
        phi_win_rate (live path) — never a raw scanner score.
        """
        try:
            import importlib.util
            gate_path = RADAR_DIR / "exchange_adapters" / "expectancy_gate.py"
            spec = importlib.util.spec_from_file_location(
                "aureon_expectancy_gate_phi", gate_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        except Exception as e:
            logger.error(f"[GATE] expectancy_gate unavailable ({e}) — REFUSING "
                         f"order ({context}) [fail-closed]")
            return {"allowed": False, "reason": "gate_error",
                    "expected_move_pct": None, "round_trip_cost_pct": None,
                    "margin_pct": None}

        conf = confidence if isinstance(confidence, (int, float)) \
            and math.isfinite(confidence) else 0.0
        conf = max(0.0, min(1.0, float(conf)))
        try:
            verdict = mod.check(self._GATE_VENUE, symbol, side, qty, price, conf)
        except Exception as e:
            logger.error(f"[GATE] expectancy_gate check raised ({e}) — REFUSING "
                         f"order ({context}) [fail-closed]")
            return {"allowed": False, "reason": "gate_error",
                    "expected_move_pct": None, "round_trip_cost_pct": None,
                    "margin_pct": None}
        if not verdict.get("allowed"):
            logger.warning(
                f"[GATE] REFUSED {context}: reason={verdict.get('reason')} "
                f"venue={verdict.get('venue')} conf={conf:.2f} "
                f"expected={verdict.get('expected_move_pct')} "
                f"cost={verdict.get('round_trip_cost_pct')} "
                f"margin={verdict.get('margin_pct')} "
                f"floor={verdict.get('capture_floor_pct')} "
                f"detail={verdict.get('detail')}")
        return verdict

    # Terminal shadow statuses — a shadow in one of these is never selected
    # for live execution again (one live attempt per shadow, ever).
    SHADOW_TERMINAL_STATUSES = ("PENDING_CONFIRM", "EXECUTED", "CONFIRMED",
                                "FAILED", "REFUSED")

    def _refuse_shadow(self, shadow, reason: str):
        """Mark a shadow REFUSED so it never re-fires (bug-hunt #7).

        Gate/cap/sizing refusals are permanent for that shadow: it leaves the
        HIT candidate pool, which stops the per-cycle refusal spam.
        """
        if shadow.status != "REFUSED":
            shadow.status = "REFUSED"
            logger.info(f"[SHADOW] {shadow.symbol} {shadow.direction} marked "
                        f"REFUSED ({reason}) — will not re-fire")
        shadow._live_attempted = True

    def _reconcile_live_position(self, shadow, audit_id: str, size: float,
                                 ledger) -> Optional[str]:
        """Positions-API reconciliation after an ambiguous order result.

        Covers the timeout-after-execute case: the order call failed or
        timed out, but the broker may have executed it. Returns the adopted
        dealId when a matching open position is found server-side, else None
        (caller marks the shadow FAILED — never retried).
        """
        try:
            positions = self.capital_dual.get_live_positions()
        except Exception as e:
            logger.error(f"[HONEY POT] positions reconciliation FAILED "
                         f"({shadow.symbol}): {e} — shadow marked FAILED "
                         f"(no retry) [fail-closed]")
            return None

        cap_direction = shadow.direction.upper()
        if cap_direction == "LONG":
            cap_direction = "BUY"
        elif cap_direction == "SHORT":
            cap_direction = "SELL"

        for pos in positions or []:
            if not isinstance(pos, dict):
                continue
            deal_id = pos.get("position", {}).get("dealId")
            if not deal_id:
                continue
            market = pos.get("market", {})
            epic = (market.get("epic") or "").upper()
            direction = (pos.get("position", {}).get("direction") or "").upper()
            # Match by epic, falling back to symbol substring
            symbol_match = epic == shadow.symbol.upper() or \
                shadow.symbol.upper() in epic
            if symbol_match and direction == cap_direction:
                logger.warning(f"[HONEY POT] RECONCILED: open position found "
                               f"server-side for {shadow.symbol} dealId={deal_id} "
                               f"— adopting (order result was ambiguous)")
                ledger.capital_confirmed(audit_id, deal_id, {"reconciled": True})
                return deal_id

        logger.info(f"[HONEY POT] Reconciliation: no open {shadow.symbol} "
                    f"{cap_direction} position server-side — order did not execute")
        return None

    def _adopt_honey_pot(self, shadow, deal_id: str, size: float, venue: str = "capital"):
        """Open the honey pot for a confirmed/reconciled live position."""
        self.honey_ladder.open_honey_pot(shadow=shadow, deal_id=deal_id, size=size)
        shadow.status = "CONFIRMED"

        # Track this live position in the concurrent-positions list.
        pot = self.honey_ladder.honey_pot
        if pot is not None:
            pot.venue = venue
            pot._live_path = "honey_pot"
            pot.max_hold_seconds = self._max_hold_seconds(pot.symbol)
            self.live_positions.append(pot)
            self._attach_dtp(pot)

        self.live_trades_today += 1
        self._save_state()

    def _log_order_failed(self, audit_id: str, shadow, size: float,
                          entry_price: float, target_price: float, error: str):
        from aureon_trade_ledger import TradeAuditRecord, asdict
        fail_record = TradeAuditRecord(
            audit_id=audit_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            stage="ORDER_FAILED",
            symbol=shadow.symbol,
            direction=shadow.direction,
            size=size,
            entry_price=entry_price,
            target_price=target_price,
            deal_id=None,
            capital_position_id=None,
            capital_confirmed=False,
            pnl=None,
            error=error,
            source=shadow.source,
            rung=shadow.ladder_rung
        )
        with open(Path(__file__).parent / "trade_ledger.jsonl", 'a') as f:
            f.write(json.dumps(asdict(fail_record)) + '\n')

    def _matrix_approves(self, shadow, current_price: float) -> bool:
        """Execution-time re-check through RadarProbabilityMatrix. Fail-closed.

        Reuses the confidence recorded at matrix admission (shadow._matrix_conf)
        with a fresh price history, so the decision reflects current volatility,
        momentum, and the matrix's learned source accuracy. Returns False on any
        error, missing admission record, or sub-threshold adjusted probability.
        """
        admission_conf = getattr(shadow, '_matrix_conf', None)
        if not isinstance(admission_conf, (int, float)) or \
                isinstance(admission_conf, bool) or not math.isfinite(admission_conf):
            logger.warning(f"[PROB] EXEC REFUSED: {shadow.symbol} has no recorded "
                           f"matrix admission confidence [fail-closed]")
            return False
        try:
            from radar_probability_matrix import evaluate_signal, should_trade
            intel = evaluate_signal(
                symbol=shadow.symbol,
                direction=shadow.direction,
                confidence=admission_conf,
                source=shadow.source,
                price_history=self.price_history.get(shadow.symbol, [current_price]),
            )
            ok = bool(should_trade(intel, min_threshold=self._probability_threshold()))
            if not ok:
                logger.warning(f"[PROB] EXEC BLOCKED: {shadow.symbol} {shadow.direction} "
                               f"adjusted_prob={intel.adjusted_probability:.1%} "
                               f"action={intel.action} risks={intel.risk_flags}")
            else:
                logger.info(f"[PROB] EXEC APPROVED: {shadow.symbol} "
                            f"adjusted_prob={intel.adjusted_probability:.1%}")
            return ok
        except Exception as e:
            logger.error(f"[PROB] EXEC BLOCKED: matrix re-check raised {e} "
                         f"[fail-closed]")
            return False

    def _execute_honey_pot(self, shadow):
        """Execute a single live trade for the honey pot with full audit.

        AUDIT TRAIL:
          1. SHADOW_HIT (already logged)
          2. ORDER_SENT (log before placing)
          3. CAPITAL_CONFIRMED / ORDER_FAILED (validate with positions API)
          4. POSITION_CLOSED (when target hit)

        IDEMPOTENCY (bug-hunt #1): the shadow is marked PENDING_CONFIRM and
        _live_attempted BEFORE the order is placed, so a network timeout
        after broker execution can never cause a duplicate: the shadow is no
        longer a HIT candidate. On any ambiguous/failed result the positions
        API reconciles first (adopting an orphaned position) and the shadow
        is terminal either way — exactly one live attempt per shadow.

        SKIPS crypto symbols — Capital.com does not support crypto CFDs.
        """
        # One live attempt per shadow, ever.
        if getattr(shadow, "_live_attempted", False) or \
                shadow.status in self.SHADOW_TERMINAL_STATUSES:
            logger.debug(f"[HONEY POT] skip {shadow.symbol}: shadow already "
                         f"attempted/terminal (status={shadow.status})")
            return

        # 🚦 BELT-AND-BRACES capability gate (the connector re-checks too,
        # immediately before any network call). Fail-closed. Refusal is
        # permanent for this shadow — no per-cycle re-fire spam (#7).
        if not self._live_trading_gate_allowed(
                f"{shadow.symbol} {shadow.direction} rung={shadow.ladder_rung}"):
            self._refuse_shadow(shadow, "capability gate refused")
            return

        # Daily live-trade cap (env RADAR_MAX_LIVE_TRADES_PER_DAY, default 3)
        if self._daily_live_cap_reached():
            self._refuse_shadow(shadow, "daily live cap reached")
            return

        # Initialize ledger if not present
        if not hasattr(self, '_trade_ledger'):
            from aureon_trade_ledger import TradeLedger
            self._trade_ledger = TradeLedger(self.capital_live)

        ledger = self._trade_ledger

        # Get or create audit ID for this shadow
        audit_id = getattr(shadow, '_audit_id', None)
        if not audit_id:
            # Log shadow hit if not already done
            audit_id = ledger.shadow_hit(
                symbol=shadow.symbol,
                direction=shadow.direction,
                entry_price=shadow.entry_price,
                target_price=shadow.target_price,
                source=shadow.source,
                rung=shadow.ladder_rung
            )
            shadow._audit_id = audit_id

        try:
            if not self.capital_dual.authenticated:
                if not self.capital_dual.authenticate():
                    logger.warning("Cannot execute: Capital.com not authenticated")
                    self._refuse_shadow(shadow, "not authenticated")
                    return

            balance = self.capital_live.get_account_balance()
            if not isinstance(balance, (int, float)) or balance < 50:
                logger.warning(f"Low balance: £{balance}")
                return

            # Get current price for sizing — FAIL-CLOSED: no synthetic
            # fallback, and stale (>90s) quotes refuse the trade.
            current_price = self._get_price(shadow.symbol,
                                            max_age_sec=self.price_stale_after_sec)
            if not current_price:
                logger.warning(f"[HONEY POT] REFUSED: no fresh price for "
                               f"{shadow.symbol} (synthetic/stale quotes are "
                               f"never used for live sizing) [fail-closed]")
                self._refuse_shadow(shadow, "no fresh price (synthetic/stale refused)")
                return

            # 🧠 PROBABILITY MATRIX RE-VALIDATION at execution time. The
            # admission gate ran when the shadow was created; market state and
            # the matrix's learned source accuracy have moved since. A shadow
            # without a recorded admission confidence (pre-fix legacy run) is
            # refused [fail-closed] — probability can never be assumed.
            if not self._matrix_approves(shadow, current_price):
                self.honey_ladder.honey_pot = type('HoneyPot', (), {'active': False})()
                self._refuse_shadow(shadow, "probability matrix re-check failed")
                return

            # Calculate dynamic size based on rung and balance
            size = self._calculate_position_size(
                symbol=shadow.symbol,
                price=current_price,
                rung=shadow.ladder_rung
            )
            if not size or size <= 0:
                self.honey_ladder.honey_pot = type('HoneyPot', (), {'active': False})()
                self._refuse_shadow(shadow, "position size zero/invalid (fail-closed)")
                return
            
            # Normalize direction
            cap_direction = shadow.direction.upper()
            if cap_direction == "LONG":
                cap_direction = "BUY"
            elif cap_direction == "SHORT":
                cap_direction = "SELL"

            # Notional sanity cap (env RADAR_MAX_NOTIONAL_PCT, default 150)
            if self._notional_cap_exceeded(shadow.symbol, size, current_price, balance):
                self.honey_ladder.honey_pot = type('HoneyPot', (), {'active': False})()
                self._refuse_shadow(shadow, "notional cap exceeded")
                return

            # Mandatory broker-side stop loss (env RADAR_STOP_LOSS_PCT, default 1.5%)
            stop_level = self._compute_stop_level(shadow.symbol, cap_direction, current_price)
            if stop_level is None:
                # refusal already logged by _compute_stop_level [fail-closed]
                self.honey_ladder.honey_pot = type('HoneyPot', (), {'active': False})()
                self._refuse_shadow(shadow, "stop loss computation failed")
                return

            # 🚦 EXPECTANCY GATE (Gary's decree): the live order must clear
            # 1.25x the venue's real round-trip cost on the confidence-scaled
            # expected move. Confidence is the source's MEASURED phi_win_rate
            # (calibrated 0..1 from real shadow outcomes) — an unknown source
            # falls back to 0.0 and is refused [fail-closed].
            _rec = self.honey_ladder.source_records.get(shadow.source)
            _win_rate = float(_rec.phi_win_rate) if _rec is not None else 0.0
            _lgv = self._expectancy_gate_verdict(
                shadow.symbol, cap_direction, size, current_price, _win_rate,
                f"live {shadow.symbol} {shadow.direction} rung={shadow.ladder_rung}")
            if not _lgv.get("allowed"):
                self.honey_ladder.honey_pot = type('HoneyPot', (), {'active': False})()
                self._refuse_shadow(
                    shadow, f"expectancy gate refused ({_lgv.get('reason')})")
                return

            # Place order — stop loss MANDATORY
            # Owner decree 2026-09-06: the live TP must sit at or beyond the
            # capture floor (>= 1.0% gain). The shadow target was already
            # clamped at add_shadow time; re-apply at execution time against
            # the actual entry price (call-time read) so no path to this
            # order can carry a sub-floor TP. Upward-only; floor absent =>
            # target unchanged (prior behavior).
            profit_level = round(
                self._floor_clamp_tp(shadow.direction, current_price,
                                     shadow.target_price), 2)

            # ── IDEMPOTENCY MARK (bug-hunt #1): before placing, take the
            # shadow out of the HIT pool and record the attempt, persisted
            # so a restart cannot re-attempt either (#2).
            shadow.status = "PENDING_CONFIRM"
            shadow._live_attempted = True
            self._save_state()

            # Log ORDER_SENT
            ledger.order_sent(
                audit_id=audit_id,
                symbol=shadow.symbol,
                direction=shadow.direction,
                size=size,
                entry_price=current_price,
                target_price=profit_level,
                source=shadow.source,
                rung=shadow.ladder_rung
            )

            logger.info(f"[HONEY POT] EXECUTING: {shadow.symbol} {shadow.direction} "
                       f"size={size} TP={profit_level} source={shadow.source} rung={shadow.ladder_rung}")

            # Aggregate exposure check for visibility (router enforces the cap).
            exposure = self.router.aggregate_exposure()
            logger.info(f"[HONEY POT] Aggregate exposure before order: "
                       f"{exposure['position_exposure']:.2f}/{exposure['limit']:.2f} "
                       f"({exposure['utilization_pct']:.1f}% utilized)")

            result = self.router.place_order(
                symbol=shadow.symbol,
                direction=cap_direction,
                size=size,
                stop_level=stop_level,  # MANDATORY broker-side stop loss
                profit_level=profit_level
            )

            deal_id = result.get("dealId")
            error = result.get("error")
            if deal_id and not error and deal_id not in ("", "unknown"):
                venue = result.get("venue", "capital")

                # For Capital.com we still validate against the positions API;
                # other venues are trusted by their own deal/tx IDs for now.
                confirmed = True
                if venue == "capital":
                    confirmed = ledger.capital_confirmed(audit_id, deal_id, result)

                if confirmed:
                    self._adopt_honey_pot(shadow, deal_id, size, venue=venue)
                    logger.info(f"[HONEY POT] LIVE: {shadow.symbol} size={size} "
                               f"dealId={deal_id} venue={venue} (CONFIRMED)")
                else:
                    logger.warning(f"[HONEY POT] dealId returned but NOT CONFIRMED in positions: {deal_id}")
                    # Reconcile with positions API before deciding the order
                    # truly failed — the position may exist under another ref.
                    reconciled_id = self._reconcile_live_position(shadow, audit_id, size, ledger)
                    if reconciled_id:
                        self._adopt_honey_pot(shadow, reconciled_id, size, venue=venue)
                    else:
                        shadow.status = "FAILED"
                        self.honey_ladder.honey_pot = type('HoneyPot', (), {'active': False})()
            else:
                # Log failure
                error = error or str(result)
                logger.error(f"[HONEY POT] FAILED: {error}")

                # Permanent refusal for known non-retryable venue constraints so
                # the shadow does not spam every cycle (Alpaca short-disabled,
                # insufficient buying power, etc.). Reconciliation is skipped
                # because the order never reached the broker.
                non_retryable = (
                    "short selling disabled",
                    "shorting_enabled=false",
                    "insufficient buying power",
                    "account is not allowed to short",
                )
                if any(k.lower() in str(error).lower() for k in non_retryable):
                    self._refuse_shadow(
                        shadow, f"non-retryable venue error: {error[:160]}")
                    self._log_order_failed(audit_id, shadow, size, current_price,
                                           profit_level, error)
                    return

                # The order call failed, but the broker may have executed it
                # before the failure (timeout-after-execute). For Capital.com,
                # reconcile with the positions API before allowing any future attempt.
                reconciled_id = self._reconcile_live_position(shadow, audit_id, size, ledger)
                if reconciled_id:
                    self._adopt_honey_pot(shadow, reconciled_id, size, venue="capital")
                else:
                    self._log_order_failed(audit_id, shadow, size, current_price,
                                           profit_level, error)
                    shadow.status = "FAILED"
                    self.honey_ladder.honey_pot = type('HoneyPot', (), {'active': False})()

        except Exception as e:
            logger.error(f"_execute_honey_pot error: {e}")
            # Even on exception, reconcile with the positions API first —
            # the order may have executed before the exception.
            try:
                reconciled_id = self._reconcile_live_position(shadow, audit_id, 0.0, ledger)
            except Exception as rec_err:
                logger.error(f"[HONEY POT] reconciliation error: {rec_err}")
                reconciled_id = None
            if reconciled_id:
                self._adopt_honey_pot(shadow, reconciled_id, 0.0)
            else:
                self._log_order_failed(audit_id, shadow, 0.0, 0.0, 0.0, str(e))
                shadow.status = "FAILED"
    
    # ── DYNAMIC TAKE PROFIT / DEAD MAN'S SWITCH ──

    _DTP_FEE_RATES = {
        "capital": 0.0015,   # spread approximation per side
        "kraken": 0.0026,    # taker
        "binance": 0.0010,   # taker
        "alpaca": 0.0000,    # commission-free
    }

    def _is_homing_symbol(self, symbol: str) -> bool:
        return (
            self.homing_target is not None
            and self.homing_target.symbol == symbol.upper()
            and self.homing_target.is_valid()
        )

    def _dtp_thresholds(self, pot: HoneyPot) -> Tuple[float, float]:
        """Return (activation_gbp, trailing_pct) for a position.

        Priority: play-board optimizer > homing mode > upstream default.
        The play board can tighten the dead-man switch for news/event plays
        or loosen it for swing plays.
        """
        exec_plan = (self.current_play_plan or {}).get("execution") or {}
        if exec_plan.get("action") == "EXECUTE":
            activation = exec_plan.get("dtp_activation_gbp")
            trail = exec_plan.get("dtp_trail_pct")
            if isinstance(activation, (int, float)) and isinstance(trail, (int, float)):
                return float(activation), float(trail)
        if self._is_homing_symbol(pot.symbol):
            return 0.01, 0.005   # £0.01 activation, 0.5% trail
        return 1.27, 0.02       # upstream default £1.27, 2% trail

    def _size_boost(self, symbol: str) -> float:
        """Concentrate fire on the locked homing target and/or selected play."""
        mult = 1.0
        if self._is_homing_symbol(symbol):
            try:
                mult *= float(os.getenv("HOMING_SIZE_MULTIPLIER", "2.0"))
            except Exception:
                mult *= 2.0
        exec_plan = (self.current_play_plan or {}).get("execution") or {}
        if exec_plan.get("action") == "EXECUTE":
            try:
                mult *= float(exec_plan.get("size_multiplier", 1.0))
            except Exception:
                pass
        return mult

    def _max_hold_seconds(self, symbol: str, default: float = None) -> float:
        """Play-board selected plays can request longer or shorter holds."""
        exec_plan = (self.current_play_plan or {}).get("execution") or {}
        if exec_plan.get("action") == "EXECUTE":
            mins = exec_plan.get("max_hold_minutes")
            if isinstance(mins, (int, float)):
                return float(mins) * 60.0
        return default if default is not None else self.honey_ladder.max_hold_seconds

    def _attach_dtp(self, pot: HoneyPot):
        """Attach a DynamicTakeProfit dead-man's switch to a live position."""
        if not _HAS_DTP or create_dtp_for_position is None:
            return
        try:
            venue = getattr(pot, 'venue', 'capital').lower()
            fee_rate = self._DTP_FEE_RATES.get(venue, 0.0015)
            activation_gbp, trail_pct = self._dtp_thresholds(pot)
            pot._dtp = create_dtp_for_position(
                entry_price=float(pot.entry_price),
                quantity=float(pot.size),
                fee_rate=fee_rate,
                gbp_usd_rate=1.27,  # conservative fallback; FX update later
                activation_threshold_gbp=activation_gbp,
            )
            pot._dtp.trailing_distance_pct = trail_pct
            logger.info(f"[DTP] attached to {pot.symbol} {pot.direction} "
                        f"threshold=£{activation_gbp:.2f} trail={trail_pct:.1%} "
                        f"venue={venue} fee={fee_rate:.4f}")
        except Exception as e:
            logger.warning(f"[DTP] could not attach to {pot.symbol}: {e}")

    def _dtp_should_exit(self, pot: HoneyPot, current_price: float) -> Tuple[bool, str]:
        """Check DTP dead-man's switch. Returns (should_exit, reason)."""
        dtp = getattr(pot, '_dtp', None)
        if dtp is None:
            return False, "no dtp"
        try:
            should_exit, reason, state = dtp.update_from_price(
                entry_price=float(pot.entry_price),
                current_price=float(current_price),
                quantity=float(pot.size),
            )
            if state.activated or should_exit:
                logger.info(f"[DTP] {pot.symbol} {reason}")
            return should_exit, reason
        except Exception as e:
            logger.warning(f"[DTP] update error for {pot.symbol}: {e}")
            return False, f"error: {e}"

    def _close_live_position(self, pot: HoneyPot, current_price: float,
                             reason: str) -> bool:
        """Close a single live position through the router."""
        if pot.direction == 'LONG':
            pnl = (current_price - pot.entry_price) / pot.entry_price * 100
        else:
            pnl = (pot.entry_price - current_price) / pot.entry_price * 100

        venue = getattr(pot, 'venue', 'capital')
        close_result = self.router.close_position(
            deal_id=pot.deal_id,
            venue=venue,
            symbol=pot.symbol,
            size=pot.size,
            direction=pot.direction,
        )
        err = str(close_result.get('error') or '').lower()
        externally_closed = any(k in err for k in ('not found', '404', 'no position', 'unknown'))

        if close_result.get('success') or externally_closed:
            if externally_closed:
                logger.info(f"[LIVE] position already closed externally: "
                           f"{pot.symbol} dealId={pot.deal_id} venue={venue}")
            if hasattr(self, '_trade_ledger') and hasattr(pot, '_audit_id'):
                self._trade_ledger.position_closed(pot._audit_id, pot.deal_id, pnl)
            logger.info(f"[LIVE] CLOSED: {pot.symbol} PnL={pnl:.4f}% "
                       f"dealId={pot.deal_id} venue={venue} reason={reason}")
            return True

        logger.error(f"[LIVE] close failed for {pot.symbol} "
                     f"dealId={pot.deal_id} venue={venue}: "
                     f"{close_result.get('error')}")
        return False

    def _check_honey_pot(self):
        """Check all active live positions for target hit, DTP trigger, or expiry.

        With the one-trade-at-a-time gate relaxed, this now iterates over
        every tracked live position, closes it through the router when needed,
        and removes it from the active list.
        """
        if not self.live_positions:
            return

        still_open: List[HoneyPot] = []
        closed_any = False

        for pot in self.live_positions:
            try:
                current_price = self._get_price(pot.symbol)
                if not current_price:
                    still_open.append(pot)
                    continue

                age = time.time() - pot.opened_at
                # Ignore target_hit if we have no meaningful target (e.g.
                # reconciled broker positions whose original TP is unknown).
                has_target = (
                    isinstance(pot.target_price, (int, float))
                    and pot.target_price > 0
                )
                target_hit = (
                    has_target
                    and (
                        (pot.direction == 'LONG' and current_price >= pot.target_price) or
                        (pot.direction == 'SHORT' and current_price <= pot.target_price)
                    )
                )

                # DTP dead-man's switch: profit-only exit once activated
                dtp_exit, dtp_reason = self._dtp_should_exit(pot, current_price)

                if target_hit or dtp_exit or age > pot.max_hold_seconds:
                    close_reason = (
                        "target_hit" if target_hit else
                        "dtp_trigger" if dtp_exit else
                        "max_hold_expired"
                    )
                    if self._close_live_position(pot, current_price, close_reason):
                        closed_any = True
                        continue
                    still_open.append(pot)
                    continue

                still_open.append(pot)
            except Exception as e:
                logger.error(f"_check_honey_pot error for {pot.symbol}: {e}")
                still_open.append(pot)

        self.live_positions = still_open
        # Backward-compat: honey_ladder.honey_pot points at the newest active position
        self.honey_ladder.honey_pot = self.live_positions[-1] if self.live_positions else None
    
    def _check_demo_shadows(self):
        """Check demo positions for shadow validation.
        
        Polls demo account positions. If a shadow's demo position is profitable,
        mark the shadow as hit (validated).
        """
        try:
            demo_positions = self.capital_dual.get_demo_positions() or []
            open_deal_ids = {p.get('position', {}).get('dealId', '')
                             for p in demo_positions}

            # 🧠 DEMO-VANISH DETECTION: a deal that was confirmed open
            # server-side and is now gone, while its shadow is still OPEN,
            # closed without the validation path firing. Count a hit only if
            # it was last seen in profit (fast TP fill between polls);
            # otherwise it is a REAL MISS for the source. Without this the
            # matrix only ever received successes and drifted to ~100%.
            try:
                from radar_probability_matrix import get_matrix as _pm
                _mat = _pm()
                for shadow in self.honey_ladder.shadow_runs:
                    _deal = getattr(shadow, '_demo_deal_id', None)
                    if not _deal or shadow.status != 'OPEN' \
                            or not getattr(shadow, '_demo_seen', False) \
                            or _deal in open_deal_ids:
                        continue
                    shadow._demo_seen = False  # terminal: never re-evaluate
                    _last_upl = float(getattr(shadow, '_demo_last_upl', 0.0) or 0.0)
                    if shadow.source in self.honey_ladder.source_records:
                        _rec = self.honey_ladder.source_records[shadow.source]
                        if _last_upl > 0:
                            _rec.hits += 1
                        else:
                            _rec.misses += 1
                        _rec.total_shadows = getattr(_rec, 'total_shadows', 0) + 1
                        _rec.phi_win_rate = (_rec.hits / _rec.total_shadows
                                             if _rec.total_shadows else 0.0)
                    if _last_upl > 0:
                        shadow.status = 'HIT'
                        shadow.pnl = _last_upl
                        _mat.record_outcome(source=shadow.source, success=True)
                        logger.info(f"[DEMO] SHADOW VALIDATED (closed): {shadow.symbol} "
                                    f"{shadow.direction} last UPL=£{_last_upl:.2f}")
                    else:
                        shadow.status = 'MISS'
                        shadow.pnl = min(0.0, _last_upl)
                        _mat.record_outcome(source=shadow.source, success=False)
                        logger.info(f"[DEMO] SHADOW MISSED (closed): {shadow.symbol} "
                                    f"{shadow.direction} last UPL=£{_last_upl:.2f}")
            except Exception as _e:
                logger.debug(f"[PROB] demo-vanish learning error: {_e}")

            if not demo_positions:
                return

            for pos in demo_positions:
                position = pos.get('position', {})
                market = pos.get('market', {})
                
                epic = market.get('epic', '')
                upl = position.get('upl', 0)
                deal_id = position.get('dealId', '')
                
                # Find matching shadow by demo dealId
                for shadow in self.honey_ladder.shadow_runs:
                    if getattr(shadow, '_demo_deal_id', None) == deal_id:
                        # Sighted server-side: arm vanish detection and keep
                        # the last observed UPL for the close verdict.
                        shadow._demo_seen = True
                        try:
                            shadow._demo_last_upl = float(upl or 0.0)
                        except (TypeError, ValueError):
                            shadow._demo_last_upl = 0.0
                        if shadow.status == 'OPEN' and upl > 0:
                            # Demo position is profitable - mark as hit
                            shadow.status = 'HIT'
                            shadow.pnl = upl
                            
                            # Update source record
                            if shadow.source in self.honey_ladder.source_records:
                                record = self.honey_ladder.source_records[shadow.source]
                                record.hits += 1
                                record.total_trades += 1
                                record.phi_win_rate = record.hits / record.total_trades
                            
                            # 🧠 PROBABILITY LEARNING: Record successful shadow
                            try:
                                from radar_probability_matrix import get_matrix
                                get_matrix().record_outcome(source=shadow.source, success=True)
                                logger.debug(f"[PROB] LEARNED: {shadow.source} hit recorded")
                            except Exception as e:
                                logger.debug(f"[PROB] Learning error: {e}")
                            
                            logger.info(f"[DEMO] SHADOW VALIDATED: {shadow.symbol} "
                                       f"{shadow.direction} PnL=£{upl:.2f} dealId={deal_id}")
                            break
                        
        except Exception as e:
            logger.debug(f"_check_demo_shadows error: {e}")
    
    def _process_signal(self, signal: MarketSignal):
        """Process signal - add to shadow ladder AND place demo trade for validation.
        
        DUAL CAPITAL ARCHITECTURE:
        1. Place DEMO trade immediately (shadow validation)
        2. Track demo position P&L
        3. If demo hits target, shadow graduates to live
        """
        logger.info(f"SIGNAL: {signal.symbol} {signal.direction} conf={signal.confidence:.2f}")
        
        # Log signal
        with open(SIGNAL_LOG, 'a') as f:
            f.write(json.dumps(signal.to_dict()) + '\n')
        
        # Add shadow to ladder with micro-scalp target
        sector = self.symbol_sectors.get(signal.symbol, "commodity")
        micro_target = self.capital_dual.calculate_micro_tp(
            symbol=signal.symbol,
            direction=signal.direction,
            entry_price=signal.entry_price
        )
        self.honey_ladder.add_shadow(
            symbol=signal.symbol,
            sector=sector,
            direction=signal.direction,
            entry_price=signal.entry_price,
            source="scanner",
            target_price=micro_target
        )
        
        # Place DEMO trade for validation (skip crypto - blocked on Capital)
        # 🚦 EXPECTANCY GATE: even though this path is currently unused, any
        # future re-enablement must not bypass the fee-aware gate (fail-closed).
        _ps_dir = signal.direction.upper()
        if _ps_dir == "LONG":
            _ps_dir = "BUY"
        elif _ps_dir == "SHORT":
            _ps_dir = "SELL"
        _ps_gate = self._expectancy_gate_verdict(
            signal.symbol, _ps_dir, 1.0, signal.entry_price,
            getattr(signal, "confidence", 0.0),
            f"demo(legacy) {signal.symbol} {signal.direction}")
        if _ps_gate.get("allowed") and signal.symbol not in ["BTCUSD", "ETHUSD"]:
            try:
                # Normalize direction for Capital
                cap_direction = signal.direction.upper()
                if cap_direction == "LONG":
                    cap_direction = "BUY"
                elif cap_direction == "SHORT":
                    cap_direction = "SELL"
                
                # Capital.com CFD minimum size for demo validation
                demo_size = 1.0
                
                # Micro-scalp: 1 tick/pip profit target
                profit_level = self.capital_dual.calculate_micro_tp(
                    symbol=signal.symbol,
                    direction=signal.direction,
                    entry_price=signal.entry_price
                )
                # Owner decree 2026-09-06: demo TP honors the capture floor
                # (>= 1.0% gain), clamped upward only.
                profit_level = self._floor_clamp_tp(
                    signal.direction, signal.entry_price, profit_level)
                
                logger.info(f"[DEMO] Micro-scalp shadow: {signal.symbol} {cap_direction} "
                           f"entry={signal.entry_price} TP={profit_level} (1 tick)")
                
                result = self.capital_dual.place_demo_order(
                    symbol=signal.symbol,
                    direction=cap_direction,
                    size=demo_size,
                    profit_level=profit_level
                )
                
                if "dealId" in result:
                    # Store demo dealId in shadow for tracking
                    shadow = self.honey_ladder.shadow_runs[-1] if self.honey_ladder.shadow_runs else None
                    if shadow:
                        shadow._demo_deal_id = result["dealId"]
                        logger.info(f"[DEMO] Shadow trade placed: {signal.symbol} "
                                   f"dealId={result['dealId']}")
                else:
                    logger.warning(f"[DEMO] Failed to place shadow: {result.get('error', 'unknown')}")
            except Exception as e:
                logger.debug(f"[DEMO] Error placing shadow: {e}")
        
        logger.info(f"[SHADOW] Added {signal.symbol} to ladder for validation")
    
    def _execute_live(self, signal: MarketSignal):
        """DEPRECATED - use Honey Ladder instead."""
        logger.warning("_execute_live is deprecated - Honey Ladder manages live execution")
        
    def run_phi_cycle(self):
        """Run continuous phi-scaled monitoring cycle."""
        self.running = True
        cycle_count = 0
        
        logger.info("="*60)
        logger.info("HONEY LADDER RADAR")
        logger.info("Multi-venue live execution. Aggregate margin <= 50%.")
        logger.info("Penny profit. Shadow proves, router executes.")
        logger.info("="*60)
        
        while self.running:
            cycle_count += 1
            
            # Determine interval tier
            if cycle_count % 50 == 0:
                interval = PHI_INTERVALS["field"]
            elif cycle_count % 20 == 0:
                interval = PHI_INTERVALS["harmonic"]
            elif cycle_count % 10 == 0:
                interval = PHI_INTERVALS["return"]
            elif cycle_count % 5 == 0:
                interval = PHI_INTERVALS["growth"]
            elif cycle_count % 2 == 0:
                interval = PHI_INTERVALS["base"]
            else:
                interval = PHI_INTERVALS["anchor"]
            
            self.scan()
            
            # Print status
            status = self.honey_ladder.get_status()
            hp = status['honey_pot']
            logger.info(f"Cycle {cycle_count} | State: {self.state.value} | "
                       f"HoneyPot: {'ACTIVE' if hp['active'] else 'EMPTY'} | "
                       f"Shadows: {status['shadow_stats']['hits']} hits / {status['shadow_stats']['total']} total | "
                       f"Live today: {self.live_trades_today}")
            
            time.sleep(interval)
    
    def stop(self):
        """Stop the radar."""
        self.running = False
        logger.info("Radar stopped")

# ═══════════════════════════════════════════════════════════════════════════════
# CLI INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Aureon Phi-Radar Auto-Hive")
    parser.add_argument("--panic", action="store_true", help="PANIC mode — halt all trading")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument("--scan-once", action="store_true", help="Run single scan")
    
    args = parser.parse_args()
    
    radar = AureonPhiRadar()
    
    if args.panic:
        radar.panic()
    elif args.status:
        status = radar.honey_ladder.get_status()
        hp = status['honey_pot']
        print(f"State: {radar.state.value}")
        print(f"Honey Pot: {'ACTIVE' if hp['active'] else 'EMPTY'}")
        if hp['active']:
            print(f"  Symbol: {hp['symbol']}")
            print(f"  Held: {hp['held_seconds']:.0f}s")
        print(f"Shadows: {status['shadow_stats']['total']} total, {status['shadow_stats']['hits']} hits")
        print(f"Live trades today: {radar.live_trades_today}")
        print(f"Source Records:")
        for src, rec in status['source_records'].items():
            print(f"  {src}: rung={rec['ladder_rung']}, phi_wr={rec['phi_win_rate']}, hits={rec['hits']}")
        print(f"Sector Heat:")
        for sector, heat in status['sector_heat'].items():
            print(f"  {sector}: hit_rate={heat['hit_rate']}, sweet_spot={heat['sweet_spot']}")
        print(f"PSK: {PSK}")
    elif args.scan_once:
        radar.scan()
    else:
        # Default: run continuous cycle
        try:
            radar.run_phi_cycle()
        except KeyboardInterrupt:
            radar.stop()
            print("\nRadar halted by user")

if __name__ == "__main__":
    main()
