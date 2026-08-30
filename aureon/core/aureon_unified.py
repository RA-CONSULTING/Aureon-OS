#!/usr/bin/env python3
"""
🌊 AUREON UNIFIED ORCHESTRATOR 🌊
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

THE PROBLEM: "The left hand didn't know what the right hand was doing."

THE SOLUTION: A unified communication layer where each system reads and 
reassures the next. Each is a piece to a big puzzle.

ARCHITECTURE (from TypeScript analysis):
┌──────────────────────────────────────────────────────────────────────────┐
│                        AQTS ORCHESTRATOR                                 │
│                    (Central Command & Control)                           │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                   │
│  │ DATA        │───▶│ QGITA       │───▶│ DECISION    │                   │
│  │ INGESTION   │    │ ENGINE      │    │ FUSION      │                   │
│  └─────────────┘    └─────────────┘    └─────────────┘                   │
│        │                  │                  │                           │
│        ▼                  ▼                  ▼                           │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                   │
│  │ LIGHTHOUSE  │◀──▶│ MASTER      │◀──▶│ RISK        │                   │
│  │ METRICS     │    │ EQUATION    │    │ MANAGER     │                   │
│  └─────────────┘    └─────────────┘    └─────────────┘                   │
│        │                  │                  │                           │
│        ▼                  ▼                  ▼                           │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                   │
│  │ RAINBOW     │◀──▶│ ELEPHANT    │◀──▶│ EXECUTION   │                   │
│  │ BRIDGE      │    │ MEMORY      │    │ ENGINE      │                   │
│  └─────────────┘    └─────────────┘    └─────────────┘                   │
│        │                  │                  │                           │
│        └──────────────────┼──────────────────┘                           │
│                           ▼                                              │
│                    ┌─────────────┐                                       │
│                    │ FIRE        │                                       │
│                    │ STARTER     │                                       │
│                    └─────────────┘                                       │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘

COMMUNICATION PROTOCOL:
  1. Each system publishes its STATE to the shared BUS
  2. Each system reads DEPENDENCIES from the BUS before acting
  3. Each system validates its output against PEER outputs
  4. Consensus required for trade execution

Author: Gary Leckey / Aureon System
"""
import os, sys, time, logging, argparse, json, math
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, TYPE_CHECKING
from urllib.parse import urlparse
from decimal import Decimal, ROUND_DOWN
from dataclasses import dataclass, field, asdict
if TYPE_CHECKING:
    from aureon.exchanges.binance_client import BinanceClient

logger = logging.getLogger(__name__)

MARKET_DATA_MAX_AGE_SECONDS = 120.0
MARKET_HISTORY_MAX_AGE_SECONDS = 3600.0
PROVIDER_CLOCK_FUTURE_TOLERANCE_SECONDS = 5.0
BINANCE_TICKER_ENDPOINT = "/api/v3/ticker/24hr"
BINANCE_PROVIDER_HOSTS = {"api.binance.com", "testnet.binance.vision"}
REAL_TRUTH_STATUSES = {"real_observed", "real_derived"}


def _finite_number(
    value: Any,
    *,
    positive: bool = False,
    nonnegative: bool = False,
) -> Optional[float]:
    """Return a finite provider number without inventing a replacement."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(number):
        return None
    if positive and number <= 0:
        return None
    if nonnegative and number < 0:
        return None
    return number


def _fresh_source_timestamp(
    value: Any,
    received_at: float,
    *,
    max_age_seconds: float = MARKET_DATA_MAX_AGE_SECONDS,
) -> Optional[float]:
    source_timestamp = _finite_number(value, positive=True)
    if source_timestamp is None:
        return None
    age = received_at - source_timestamp
    if age < -PROVIDER_CLOCK_FUTURE_TOLERANCE_SECONDS or age > max_age_seconds:
        return None
    if math.isclose(source_timestamp, received_at, rel_tol=0.0, abs_tol=1e-9):
        return None
    return source_timestamp


def _runtime_bootstrap() -> None:
    """Perform optional runtime wiring only after an explicit CLI start."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass
    try:
        from aureon.core.aureon_baton_link import link_system
        link_system(__name__)
    except Exception:
        logger.debug("Baton link unavailable", exc_info=True)
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[
                logging.FileHandler("aureon_unified.log"),
                logging.StreamHandler(sys.stdout),
            ],
        )


def _state_provenance(
    state: Any,
    now: float,
    *,
    require_confidence: bool = True,
) -> Tuple[bool, str, Optional[float]]:
    if state is None or not state.ready:
        return False, "state_not_ready", None
    coherence = _finite_number(state.coherence, nonnegative=True)
    if coherence is None or coherence > 1:
        return False, "coherence_missing_or_malformed", None
    if require_confidence:
        confidence = _finite_number(state.confidence, nonnegative=True)
        if confidence is None or confidence > 1:
            return False, "confidence_missing_or_malformed", None
    data = state.data
    if not isinstance(data, dict):
        return False, "state_provenance_missing", None
    if data.get("truth_status") not in REAL_TRUTH_STATUSES:
        return False, "state_truth_status_ineligible", None
    if data.get("generated") is not False:
        return False, "generated_state_ineligible", None
    if not isinstance(data.get("provider_id"), str) or not data["provider_id"]:
        return False, "provider_identity_missing", None
    if not isinstance(data.get("source_id"), str) or not data["source_id"]:
        return False, "source_identity_missing", None
    received_at = _finite_number(data.get("received_at"), positive=True)
    if received_at is None:
        return False, "receipt_timestamp_missing", None
    state_timestamp = _finite_number(state.timestamp, positive=True)
    if state_timestamp is None or not math.isclose(
        state_timestamp,
        received_at,
        rel_tol=0.0,
        abs_tol=1e-6,
    ):
        return False, "state_receipt_timestamp_mismatch", None
    if received_at > now + PROVIDER_CLOCK_FUTURE_TOLERANCE_SECONDS:
        return False, "receipt_timestamp_in_future", None
    source_timestamp = _fresh_source_timestamp(
        data.get("source_timestamp"),
        now,
    )
    if source_timestamp is None:
        return False, "source_timestamp_missing_or_stale", None
    if math.isclose(source_timestamp, received_at, rel_tol=0.0, abs_tol=1e-9):
        return False, "source_and_receipt_timestamp_not_distinct", None
    if source_timestamp > received_at + PROVIDER_CLOCK_FUTURE_TOLERANCE_SECONDS:
        return False, "source_timestamp_after_receipt", None
    return True, "", source_timestamp

# ═══════════════════════════════════════════════════════════════════════════
# UNIFIED STATE BUS - THE COMMUNICATION LAYER
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class SystemState:
    """State published by each system to the bus"""
    system_name: str
    timestamp: float
    ready: bool
    coherence: Optional[float] = None
    confidence: Optional[float] = None
    signal: str = 'NEUTRAL'  # 'BUY', 'SELL', 'NEUTRAL'
    data: Dict[str, Any] = field(default_factory=dict)

class UnifiedBus:
    """
    Central communication bus where all systems publish and read state.
    
    "Each system reads and reassures the next. Each is a piece to a big puzzle."
    """
    
    def __init__(self):
        self.states: Dict[str, SystemState] = {}
        self.history: List[Dict[str, SystemState]] = []
        self.lock = False  # Simple mutex for atomic updates
    
    def publish(self, state: SystemState):
        """Publish system state to the bus"""
        while self.lock:
            time.sleep(0.001)
        self.lock = True
        self.states[state.system_name] = state
        self.lock = False
        
        coherence = (
            f"{state.coherence:.3f}"
            if _finite_number(state.coherence) is not None
            else "no_data"
        )
        logger.debug(
            "BUS: %s published | coherence=%s | signal=%s",
            state.system_name,
            coherence,
            state.signal,
        )
    
    def read(self, system_name: str) -> Optional[SystemState]:
        """Read another system's state"""
        return self.states.get(system_name)
    
    def read_all(self) -> Dict[str, SystemState]:
        """Read all system states"""
        return self.states.copy()
    
    def snapshot(self) -> Dict[str, Any]:
        """Take a snapshot of the entire bus state"""
        return {name: asdict(state) for name, state in self.states.items()}
    
    def check_consensus(self, required_systems: List[str], min_coherence: float = 0.7) -> Tuple[bool, str]:
        """
        Check if all required systems are ready and aligned.
        
        Returns: (consensus_achieved, signal)
        """
        signals = []
        coherences = []
        
        for sys_name in required_systems:
            state = self.states.get(sys_name)
            if state is None:
                return False, f"{sys_name} not reporting"
            eligible, reason, _ = _state_provenance(state, time.time())
            if not eligible:
                return False, f"{sys_name} provenance ineligible ({reason})"
            if state.coherence is None:
                return False, f"{sys_name} coherence unavailable"
            if state.coherence < min_coherence:
                return False, f"{sys_name} coherence too low ({state.coherence:.3f})"
            
            signals.append(state.signal)
            coherences.append(state.coherence)
        
        # Check signal alignment
        buy_votes = signals.count('BUY')
        sell_votes = signals.count('SELL')
        neutral_votes = signals.count('NEUTRAL')
        
        if buy_votes > sell_votes and buy_votes > neutral_votes:
            return True, 'BUY'
        elif sell_votes > buy_votes and sell_votes > neutral_votes:
            return True, 'SELL'
        else:
            return True, 'NEUTRAL'

# Global bus instance
BUS = UnifiedBus()

# ═══════════════════════════════════════════════════════════════════════════
# SYSTEM 1: DATA INGESTION
# ═══════════════════════════════════════════════════════════════════════════

class DataIngestionSystem:
    """
    Ingests market data from Binance.
    Publishes: prices, volumes, order book depth, funding rates
    """
    
    NAME = "DataIngestion"
    
    def __init__(self, client: Optional["BinanceClient"]):
        self.client = client
        self.ticker_cache: Dict[str, Dict[str, Any]] = {}
        self.price_history: Dict[str, List[float]] = {}
        self.volume_history: Dict[str, List[float]] = {}
        self.observation_history: Dict[str, List[Dict[str, Any]]] = {}
        self.last_update: Optional[float] = None
        self.last_receipt: Dict[str, Any] = {
            "truth_status": "no_data",
            "no_data_reason": "provider_not_queried",
            "provider_id": "binance",
            "source_id": BINANCE_TICKER_ENDPOINT,
            "source_timestamp": None,
            "received_at": None,
        }

    @staticmethod
    def _normalise_ticker(
        row: Any,
        received_at: float,
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        if not isinstance(row, dict):
            return None, "ticker_row_not_object"
        symbol = row.get("symbol")
        if not isinstance(symbol, str) or not symbol.strip():
            return None, "ticker_symbol_missing"
        symbol = symbol.strip().upper()
        required_fields = (
            "lastPrice",
            "quoteVolume",
            "highPrice",
            "lowPrice",
            "priceChangePercent",
            "closeTime",
        )
        if any(field_name not in row for field_name in required_fields):
            return None, f"incomplete_ticker_fields:{symbol}"

        price = _finite_number(row["lastPrice"], positive=True)
        volume = _finite_number(row["quoteVolume"], positive=True)
        high = _finite_number(row["highPrice"], positive=True)
        low = _finite_number(row["lowPrice"], positive=True)
        change = _finite_number(row["priceChangePercent"])
        close_time_ms = _finite_number(row["closeTime"], positive=True)
        if None in (price, volume, high, low, change, close_time_ms):
            return None, f"malformed_ticker_values:{symbol}"
        if low > price or price > high:
            return None, f"inconsistent_ticker_range:{symbol}"

        source_timestamp = _fresh_source_timestamp(
            close_time_ms / 1000.0,
            received_at,
        )
        if source_timestamp is None:
            return None, f"missing_or_stale_provider_timestamp:{symbol}"

        normalised = dict(row)
        normalised.update(
            {
                "symbol": symbol,
                "lastPrice": price,
                "quoteVolume": volume,
                "highPrice": high,
                "lowPrice": low,
                "priceChangePercent": change,
                "closeTime": close_time_ms,
                "provider_id": "binance",
                "source_id": f"binance:spot:24hr:{symbol}",
                "provider_endpoint": BINANCE_TICKER_ENDPOINT,
                "source_timestamp": source_timestamp,
                "received_at": received_at,
                "truth_status": "real_observed",
                "generated": False,
            }
        )
        return normalised, ""

    @staticmethod
    def _observation_is_eligible(
        observation: Any,
        now: float,
        *,
        max_age_seconds: float,
    ) -> bool:
        if not isinstance(observation, dict):
            return False
        if observation.get("provider_id") != "binance":
            return False
        if observation.get("truth_status") != "real_observed":
            return False
        if observation.get("generated") is not False:
            return False
        if not isinstance(observation.get("source_id"), str):
            return False
        received_at = _finite_number(observation.get("received_at"), positive=True)
        if received_at is None:
            return False
        if received_at > now + PROVIDER_CLOCK_FUTURE_TOLERANCE_SECONDS:
            return False
        source_timestamp = _fresh_source_timestamp(
            observation.get("source_timestamp"),
            now,
            max_age_seconds=max_age_seconds,
        )
        if source_timestamp is None:
            return False
        if math.isclose(source_timestamp, received_at, rel_tol=0.0, abs_tol=1e-9):
            return False
        if source_timestamp > received_at + PROVIDER_CLOCK_FUTURE_TOLERANCE_SECONDS:
            return False
        required = (
            _finite_number(observation.get("lastPrice"), positive=True),
            _finite_number(observation.get("quoteVolume"), positive=True),
            _finite_number(observation.get("highPrice"), positive=True),
            _finite_number(observation.get("lowPrice"), positive=True),
            _finite_number(observation.get("priceChangePercent")),
        )
        if any(value is None for value in required):
            return False
        price, _, high, low, _ = required
        return bool(low <= price <= high)

    def _publish_no_data(self, reason: str, received_at: float) -> Dict[str, Any]:
        self.ticker_cache = {}
        self.last_receipt = {
            "truth_status": "no_data",
            "no_data_reason": reason,
            "provider_id": "binance",
            "source_id": BINANCE_TICKER_ENDPOINT,
            "source_timestamp": None,
            "received_at": received_at,
        }
        BUS.publish(
            SystemState(
                system_name=self.NAME,
                timestamp=received_at,
                ready=False,
                signal="HOLD",
                data=dict(self.last_receipt),
            )
        )
        return dict(self.last_receipt)
    
    def update(self) -> Dict[str, Any]:
        """Fetch, validate, and atomically publish current Binance observations."""
        received_at = time.time()
        if self.client is None:
            return self._publish_no_data("provider_client_unavailable", received_at)
        provider_host = urlparse(str(getattr(self.client, "base", ""))).hostname
        if provider_host not in BINANCE_PROVIDER_HOSTS:
            return self._publish_no_data(
                "provider_identity_or_endpoint_mismatch",
                received_at,
            )
        try:
            response = self.client.session.get(
                f"{self.client.base}{BINANCE_TICKER_ENDPOINT}",
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list) or not payload:
                return self._publish_no_data(
                    "provider_payload_empty_or_malformed",
                    received_at,
                )

            accepted: Dict[str, Dict[str, Any]] = {}
            rejected_reasons: List[str] = []
            for row in payload:
                ticker, reason = self._normalise_ticker(row, received_at)
                if ticker is None:
                    rejected_reasons.append(reason)
                    continue
                accepted[ticker["symbol"]] = ticker

            if not accepted:
                reason = rejected_reasons[0] if rejected_reasons else "no_complete_tickers"
                return self._publish_no_data(reason, received_at)

            self.ticker_cache = accepted
            for symbol, observation in accepted.items():
                history = self.observation_history.setdefault(symbol, [])
                source_timestamp = observation["source_timestamp"]
                if not history or source_timestamp > history[-1]["source_timestamp"]:
                    history.append(dict(observation))
                    del history[:-100]
                self.price_history[symbol] = [item["lastPrice"] for item in history]
                self.volume_history[symbol] = [item["quoteVolume"] for item in history]

            self.last_update = received_at
            oldest_source_timestamp = min(
                observation["source_timestamp"] for observation in accepted.values()
            )
            self.last_receipt = {
                "truth_status": "real_observed",
                "provider_id": "binance",
                "source_id": BINANCE_TICKER_ENDPOINT,
                "source_timestamp": oldest_source_timestamp,
                "received_at": received_at,
                "symbols_loaded": len(accepted),
                "rows_rejected": len(rejected_reasons),
                "generated": False,
            }
            BUS.publish(
                SystemState(
                    system_name=self.NAME,
                    timestamp=received_at,
                    ready=True,
                    coherence=1.0,
                    confidence=1.0,
                    signal="NEUTRAL",
                    data=dict(self.last_receipt),
                )
            )
            return dict(self.last_receipt)
        except Exception as e:
            logger.error(f"❌ DataIngestion error: {e}")
            return self._publish_no_data(
                f"provider_request_failed:{type(e).__name__}",
                received_at,
            )
    
    def get_ticker(self, symbol: str) -> Optional[Dict]:
        observation = self.ticker_cache.get(symbol.upper())
        if not self._observation_is_eligible(
            observation,
            time.time(),
            max_age_seconds=MARKET_DATA_MAX_AGE_SECONDS,
        ):
            return None
        return dict(observation)

    def get_observations(self, symbol: str, minimum: int) -> List[Dict[str, Any]]:
        history = self.observation_history.get(symbol.upper(), [])
        now = time.time()
        eligible = [
            dict(observation)
            for observation in history
            if self._observation_is_eligible(
                observation,
                now,
                max_age_seconds=MARKET_HISTORY_MAX_AGE_SECONDS,
            )
        ]
        timestamps = [item["source_timestamp"] for item in eligible]
        if any(current <= previous for previous, current in zip(timestamps, timestamps[1:])):
            return []
        if len(eligible) < minimum:
            return []
        return eligible
    
    def get_price(self, symbol: str) -> Optional[float]:
        ticker = self.get_ticker(symbol)
        if ticker is None:
            return None
        return ticker["lastPrice"]
    
    def get_btc_price(self) -> Optional[float]:
        return self.get_price("BTCUSDT")

# ═══════════════════════════════════════════════════════════════════════════
# SYSTEM 2: LIGHTHOUSE METRICS (from lighthouseMetrics.ts)
# ═══════════════════════════════════════════════════════════════════════════

class LighthouseSystem:
    """
    Computes |Q| (anomaly pointer) and G_eff (effective gravity).
    These are the "flame" and "brake" metrics from the ablation study.
    """
    
    NAME = "Lighthouse"
    PHI = 1.618033988749
    PHI_INV = 1 / PHI
    
    def __init__(self, data_system: DataIngestionSystem):
        self.data = data_system
    
    def compute_anomaly_pointer(self, symbol: str) -> Optional[float]:
        """
        |Q| = Flame metric - spikes during sudden change
        """
        ticker = self.data.get_ticker(symbol)
        observations = self.data.get_observations(symbol, 10)
        if ticker is None or not observations:
            return None

        prices = [observation["lastPrice"] for observation in observations]
        volumes = [observation["quoteVolume"] for observation in observations]
        
        # Volume spike
        recent_vol = volumes[-10:]
        mean_vol = sum(recent_vol) / len(recent_vol)
        if mean_vol <= 0:
            return None
        current_vol = ticker["quoteVolume"]
        volume_spike = min(1.0, current_vol / mean_vol)
        
        # Spread anomaly
        high = ticker["highPrice"]
        low = ticker["lowPrice"]
        price = ticker["lastPrice"]
        spread_ratio = (high - low) / price
        spread_anomaly = min(1.0, spread_ratio * 10)
        
        # Price acceleration
        recent = prices[-5:]
        diffs = [recent[i] - recent[i-1] for i in range(1, len(recent))]
        accel = [abs(diffs[i] - diffs[i-1]) for i in range(1, len(diffs))]
        if not accel:
            return None
        mean_accel = sum(accel) / len(accel)
        price_accel = min(1.0, mean_accel / (price * 0.001))
        
        # Weighted combination
        Q = volume_spike * 0.4 + spread_anomaly * 0.3 + price_accel * 0.3
        return min(1.0, Q)
    
    def compute_effective_gravity(self, symbol: str) -> Optional[float]:
        """
        G_eff = Brake metric - geometric curvature × Fibonacci match
        """
        observations = self.data.get_observations(symbol, 5)
        if not observations:
            return None
        prices = [observation["lastPrice"] for observation in observations]
        
        recent = prices[-5:]
        
        # Curvature (second derivative)
        p0, p1, p2 = recent[-3], recent[-2], recent[-1]
        dx1 = p1 - p0
        dx2 = p2 - p1
        curvature = abs(dx2 - dx1)
        kappa = curvature / p1
        
        # Fibonacci match (golden ratio spacing)
        # Simplified: check if price movements follow phi ratio
        if abs(dx1) > 0:
            ratio = abs(dx2) / abs(dx1)
        else:
            return None
        
        fib_match = max(0, 1 - abs(ratio - self.PHI_INV) / 0.1)
        
        # Local contrast
        local_contrast = abs(p2 - p1) / 2
        normalized_contrast = min(1.0, local_contrast / (p1 * 0.01))
        
        G_eff = kappa * fib_match * normalized_contrast * 100
        return min(1.0, G_eff)
    
    def _no_data_metrics(self, symbol: str, reason: str) -> Dict[str, Any]:
        return {
            "symbol": symbol,
            "Q": None,
            "G_eff": None,
            "C_lin": None,
            "C_nonlin": None,
            "L": None,
            "truth_status": "no_data",
            "no_data_reason": reason,
            "provider_id": "binance",
            "source_id": f"binance:spot:24hr:{symbol}",
            "source_timestamp": None,
            "received_at": time.time(),
            "action_eligible": False,
        }

    def compute_lighthouse_intensity(self, symbol: str) -> Dict[str, Any]:
        """
        L(t) = (C_lin^w1 × C_nonlin^w2 × G_eff^w3 × |Q|^w4)^(1/Σw)
        """
        Q = self.compute_anomaly_pointer(symbol)
        G_eff = self.compute_effective_gravity(symbol)
        ticker = self.data.get_ticker(symbol)
        observations = self.data.get_observations(symbol, 20)
        if Q is None or G_eff is None or ticker is None or not observations:
            return self._no_data_metrics(
                symbol,
                "incomplete_fresh_ticker_or_history",
            )

        prices = [observation["lastPrice"] for observation in observations]
        
        # Linear coherence (trend strength)
        recent = prices[-20:]
        trend = (recent[-1] - recent[0]) / recent[0]
        C_lin = min(1.0, abs(trend) / 0.05)  # 5% move = max coherence
        
        # Nonlinear coherence (inverse volatility)
        mean = sum(recent) / len(recent)
        variance = sum((p - mean) ** 2 for p in recent) / len(recent)
        volatility = math.sqrt(variance) / mean
        C_nonlin = 1.0 / (1.0 + volatility)
        
        # Lighthouse intensity (geometric mean with ablation weights)
        weights = {'C_lin': 1.0, 'C_nonlin': 1.2, 'G_eff': 1.2, 'Q': 0.8}
        total_weight = sum(weights.values())
        
        # Avoid log(0)
        C_lin = max(0.01, C_lin)
        C_nonlin = max(0.01, C_nonlin)
        G_eff = max(0.01, G_eff)
        Q = max(0.01, Q)
        
        log_sum = (
            weights['C_lin'] * math.log(C_lin) +
            weights['C_nonlin'] * math.log(C_nonlin) +
            weights['G_eff'] * math.log(G_eff) +
            weights['Q'] * math.log(Q)
        )
        
        L = math.exp(log_sum / total_weight)
        
        return {
            'symbol': symbol,
            'Q': Q,
            'G_eff': G_eff,
            'C_lin': C_lin,
            'C_nonlin': C_nonlin,
            'L': L,
            'truth_status': 'real_derived',
            'provider_id': 'binance',
            'source_id': ticker['source_id'],
            'source_timestamp': ticker['source_timestamp'],
            'received_at': time.time(),
            'action_eligible': True,
            'generated': False,
        }
    
    def evaluate(self, symbols: List[str]) -> Dict[str, Dict]:
        """Evaluate lighthouse metrics for all symbols"""
        results = {}
        requested = list(dict.fromkeys(symbols[:20]))
        eligible: List[Dict[str, Any]] = []

        for symbol in requested:
            metrics = self.compute_lighthouse_intensity(symbol)
            results[symbol] = metrics
            if metrics["truth_status"] == "real_derived":
                eligible.append(metrics)

        received_at = time.time()
        if not requested or len(eligible) != len(requested):
            BUS.publish(
                SystemState(
                    system_name=self.NAME,
                    timestamp=received_at,
                    ready=False,
                    signal="HOLD",
                    data={
                        "truth_status": "no_data",
                        "no_data_reason": "incomplete_lighthouse_evidence",
                        "provider_id": "binance",
                        "source_id": "lighthouse:binance:24hr",
                        "source_timestamp": None,
                        "received_at": received_at,
                        "symbols_requested": len(requested),
                        "symbols_eligible": len(eligible),
                    },
                )
            )
            return results

        avg_L = sum(metrics["L"] for metrics in eligible) / len(eligible)
        source_timestamp = min(
            metrics["source_timestamp"] for metrics in eligible
        )
        BUS.publish(
            SystemState(
                system_name=self.NAME,
                timestamp=received_at,
                ready=True,
                coherence=avg_L,
                confidence=avg_L,
                signal="NEUTRAL",
                data={
                    "truth_status": "real_derived",
                    "provider_id": "binance",
                    "source_id": "lighthouse:binance:24hr",
                    "source_timestamp": source_timestamp,
                    "received_at": received_at,
                    "avg_lighthouse": avg_L,
                    "symbols_evaluated": len(eligible),
                    "generated": False,
                },
            )
        )
        
        return results

# ═══════════════════════════════════════════════════════════════════════════
# SYSTEM 3: MASTER EQUATION (Λ = S + O + E)
# ═══════════════════════════════════════════════════════════════════════════

class MasterEquationSystem:
    """
    Computes Λ(t) = S(t) + O(t) + E(t)
    
    S(t) = Substrate (9 Auris Nodes)
    O(t) = Observer (market price injection)
    E(t) = Echo (feedback from previous states)
    """
    
    NAME = "MasterEquation"
    
    # 9 Auris Nodes with frequencies
    AURIS_NODES = {
        'Tiger': {'freq': 741.0, 'role': 'Disruptor'},
        'Falcon': {'freq': 852.0, 'role': 'Perception'},
        'Hummingbird': {'freq': 963.0, 'role': 'Flow'},
        'Dolphin': {'freq': 528.0, 'role': 'Signal Clarity'},
        'Deer': {'freq': 396.0, 'role': 'Grounding'},
        'Owl': {'freq': 432.0, 'role': 'Memory'},
        'Panda': {'freq': 412.3, 'role': 'Empathy Core'},
        'CargoShip': {'freq': 174.0, 'role': 'Integration'},
        'Clownfish': {'freq': 639.0, 'role': 'Symbiosis'},
    }
    
    def __init__(self, data_system: DataIngestionSystem):
        self.data = data_system
        self.lambda_history: Dict[str, List[float]] = {}
        self.lambda_receipts: Dict[str, List[Dict[str, Any]]] = {}
        self.echo_decay = 0.9  # Echo feedback decay rate
        self.last_lambda: Dict[str, float] = {}

    def prime_echo_history(
        self,
        symbol: str,
        observations: List[Dict[str, Any]],
    ) -> bool:
        """Load only explicit, fresh, provenance-bearing prior Lambda receipts."""
        now = time.time()
        accepted: List[Dict[str, Any]] = []
        for observation in observations:
            if not isinstance(observation, dict):
                return False
            value = _finite_number(observation.get("Lambda"), nonnegative=True)
            received_at = _finite_number(
                observation.get("received_at"),
                positive=True,
            )
            if value is None or value > 1 or received_at is None:
                return False
            source_timestamp = _fresh_source_timestamp(
                observation.get("source_timestamp"),
                now,
                max_age_seconds=MARKET_HISTORY_MAX_AGE_SECONDS,
            )
            if source_timestamp is None:
                return False
            if math.isclose(
                source_timestamp,
                received_at,
                rel_tol=0.0,
                abs_tol=1e-9,
            ):
                return False
            if source_timestamp > (
                received_at + PROVIDER_CLOCK_FUTURE_TOLERANCE_SECONDS
            ):
                return False
            if observation.get("truth_status") != "real_derived":
                return False
            if observation.get("provider_id") != "binance":
                return False
            if not isinstance(observation.get("source_id"), str):
                return False
            if observation.get("generated") is not False:
                return False
            normalised = dict(observation)
            normalised["Lambda"] = value
            normalised["source_timestamp"] = source_timestamp
            normalised["received_at"] = received_at
            accepted.append(normalised)

        if len(accepted) < 3:
            return False
        timestamps = [item["source_timestamp"] for item in accepted]
        if any(current <= previous for previous, current in zip(timestamps, timestamps[1:])):
            return False
        key = symbol.upper()
        self.lambda_receipts[key] = accepted[-100:]
        self.lambda_history[key] = [item["Lambda"] for item in accepted[-100:]]
        self.last_lambda[key] = self.lambda_history[key][-1]
        return True
    
    def compute_substrate(self, symbol: str) -> Optional[float]:
        """
        S(t) = Weighted sum of 9 Auris Node activations
        
        Each node activates based on different market conditions.
        """
        ticker = self.data.get_ticker(symbol)
        btc_ticker = self.data.get_ticker("BTCUSDT")
        observations = self.data.get_observations(symbol, 20)
        if ticker is None or btc_ticker is None or not observations:
            return None

        change = ticker["priceChangePercent"]
        volume = ticker["quoteVolume"]
        
        activations = []
        
        # Tiger: Activates on disruption (high volatility)
        tiger = min(1.0, abs(change) / 10.0)
        activations.append(tiger)
        
        # Falcon: Activates on perception (clear direction)
        falcon = 1.0 if abs(change) > 3.0 else 0.5
        activations.append(falcon)
        
        # Hummingbird: Flow state (steady upward)
        hummingbird = 1.0 if change > 5.0 else (0.3 if change > 0 else 0.1)
        activations.append(hummingbird)
        
        # Dolphin: Signal clarity (low noise)
        prices = [observation["lastPrice"] for observation in observations]
        mean = sum(prices[-10:]) / 10
        variance = sum((p - mean) ** 2 for p in prices[-10:]) / 10
        noise = math.sqrt(variance) / mean
        dolphin = 1.0 - min(1.0, noise * 10)
        activations.append(dolphin)
        
        # Deer: Grounding (stability near support)
        deer = 0.8 if abs(change) < 2.0 else 0.3
        activations.append(deer)
        
        # Owl: Memory (historical pattern match)
        trend_20 = (prices[-1] - prices[-20]) / prices[-20]
        owl = 0.8 if abs(trend_20) < 0.1 else 0.4
        activations.append(owl)
        
        # Panda: Empathy (market sentiment alignment)
        panda = 0.8 if change > 0 else 0.4
        activations.append(panda)
        
        # CargoShip: Integration (volume confirmation)
        cargoship = min(1.0, volume / 100.0)  # 100 BTC volume = max
        activations.append(cargoship)
        
        # Clownfish: Symbiosis (cross-market alignment)
        btc_change = btc_ticker["priceChangePercent"]
        clownfish = 1.0 if (change > 0 and btc_change > 0) or (change < 0 and btc_change < 0) else 0.3
        activations.append(clownfish)
        
        # Weighted average
        S = sum(activations) / len(activations)
        return S
    
    def compute_observer(self, symbol: str) -> Optional[float]:
        """
        O(t) = Observer component (market price injection)
        """
        ticker = self.data.get_ticker(symbol)
        if ticker is None:
            return None

        change = ticker["priceChangePercent"]
        
        # Sigmoid mapping
        O = 1.0 / (1.0 + math.exp(-change / 5.0))
        return O
    
    def compute_echo(self, symbol: str) -> Optional[float]:
        """
        E(t) = Echo component (feedback from previous Lambda)
        """
        key = symbol.upper()
        history = self.lambda_history.get(key)
        receipts = self.lambda_receipts.get(key)
        if history is None or receipts is None or len(history) < 3:
            return None
        now = time.time()
        for receipt in receipts[-10:]:
            received_at = _finite_number(receipt.get("received_at"), positive=True)
            source_timestamp = _fresh_source_timestamp(
                receipt.get("source_timestamp"),
                now,
                max_age_seconds=MARKET_HISTORY_MAX_AGE_SECONDS,
            )
            if received_at is None or source_timestamp is None:
                return None
            if math.isclose(
                source_timestamp,
                received_at,
                rel_tol=0.0,
                abs_tol=1e-9,
            ):
                return None
            if receipt.get("truth_status") != "real_derived":
                return None
        
        # Exponentially weighted average of past Lambda values
        weights = [self.echo_decay ** i for i in range(min(10, len(history)))]
        recent = history[-10:][::-1]
        
        weighted_sum = sum(w * v for w, v in zip(weights, recent))
        total_weight = sum(weights[:len(recent)])
        
        if total_weight <= 0:
            return None
        return weighted_sum / total_weight
    
    def _no_data_lambda(self, symbol: str, reason: str) -> Dict[str, Any]:
        return {
            "symbol": symbol,
            "Lambda": None,
            "S": None,
            "O": None,
            "E": None,
            "coherence": None,
            "truth_status": "no_data",
            "no_data_reason": reason,
            "provider_id": "binance",
            "source_id": f"hnc-lambda:{symbol}",
            "source_timestamp": None,
            "received_at": time.time(),
            "action_eligible": False,
        }

    def compute_lambda(self, symbol: str) -> Dict[str, Any]:
        """
        Λ(t) = S(t) + O(t) + E(t)
        
        Normalized to [0, 1] via division by 3
        """
        S = self.compute_substrate(symbol)
        O = self.compute_observer(symbol)
        E = self.compute_echo(symbol)
        ticker = self.data.get_ticker(symbol)
        if S is None or O is None or E is None or ticker is None:
            return self._no_data_lambda(
                symbol,
                "incomplete_substrate_observer_or_echo_evidence",
            )

        Lambda = (S + O + E) / 3.0
        key = symbol.upper()
        history = self.lambda_history.setdefault(key, [])
        receipts = self.lambda_receipts.setdefault(key, [])
        received_at = time.time()
        receipt = {
            "symbol": key,
            "Lambda": Lambda,
            "S": S,
            "O": O,
            "E": E,
            "truth_status": "real_derived",
            "provider_id": "binance",
            "source_id": f"hnc-lambda:{key}",
            "source_timestamp": ticker["source_timestamp"],
            "received_at": received_at,
            "generated": False,
        }
        history.append(Lambda)
        receipts.append(dict(receipt))
        del history[:-100]
        del receipts[:-100]
        self.last_lambda[key] = Lambda

        coherence: Optional[float] = None
        if len(history) >= 5:
            recent = history[-5:]
            coherence = 1.0 - min(1.0, 2 * (max(recent) - min(recent)))

        return {
            **receipt,
            "coherence": coherence,
            "action_eligible": coherence is not None,
            "no_data_reason": (
                None
                if coherence is not None
                else "insufficient_real_lambda_history_for_coherence"
            ),
        }
    
    def evaluate(self, symbols: List[str]) -> Dict[str, Dict]:
        """Evaluate Master Equation for all symbols"""
        results = {}
        requested = list(dict.fromkeys(symbols[:20]))
        eligible: List[Dict[str, Any]] = []

        for symbol in requested:
            metrics = self.compute_lambda(symbol)
            results[symbol] = metrics
            if metrics["action_eligible"]:
                eligible.append(metrics)

        received_at = time.time()
        if not requested or len(eligible) != len(requested):
            BUS.publish(
                SystemState(
                    system_name=self.NAME,
                    timestamp=received_at,
                    ready=False,
                    signal="HOLD",
                    data={
                        "truth_status": "no_data",
                        "no_data_reason": "incomplete_master_equation_evidence",
                        "provider_id": "binance",
                        "source_id": "hnc-lambda:aggregate",
                        "source_timestamp": None,
                        "received_at": received_at,
                        "symbols_requested": len(requested),
                        "symbols_eligible": len(eligible),
                    },
                )
            )
            return results

        avg_lambda = sum(metrics["Lambda"] for metrics in eligible) / len(eligible)
        avg_coherence = (
            sum(metrics["coherence"] for metrics in eligible) / len(eligible)
        )
        
        # Determine signal based on Lambda
        if avg_lambda > 0.6:
            signal = 'BUY'
        elif avg_lambda < 0.4:
            signal = 'SELL'
        else:
            signal = 'NEUTRAL'
        
        source_timestamp = min(
            metrics["source_timestamp"] for metrics in eligible
        )
        BUS.publish(
            SystemState(
                system_name=self.NAME,
                timestamp=received_at,
                ready=True,
                coherence=avg_coherence,
                confidence=avg_lambda,
                signal=signal,
                data={
                    "truth_status": "real_derived",
                    "provider_id": "binance",
                    "source_id": "hnc-lambda:aggregate",
                    "source_timestamp": source_timestamp,
                    "received_at": received_at,
                    "avg_lambda": avg_lambda,
                    "symbols_evaluated": len(eligible),
                    "generated": False,
                },
            )
        )
        
        return results

# ═══════════════════════════════════════════════════════════════════════════
# SYSTEM 4: RAINBOW BRIDGE (Emotional Frequency Mapping)
# ═══════════════════════════════════════════════════════════════════════════

class RainbowBridgeSystem:
    """
    Maps coherence to emotional frequency.
    528 Hz = LOVE = optimal trading state
    """
    
    NAME = "RainbowBridge"
    
    EMOTIONAL_FREQUENCIES = {
        'Anger': 110,
        'Fear': 174,
        'Frustration': 285,
        'Doubt': 330,
        'Worry': 396,
        'Hope': 412.3,
        'Calm': 432,
        'Neutral': 440,
        'Acceptance': 480,
        'LOVE': 528,  # THE CENTER
        'Harmony': 582,
        'Connection': 639,
        'Flow': 693,
        'Awakening': 741,
        'Clarity': 819,
        'Intuition': 852,
        'Awe': 963,
    }
    
    THE_VOW = "I trade with love, I trade with light"
    
    def get_emotional_state(self, coherence: float) -> Tuple[str, float]:
        """Map coherence (0-1) to emotional frequency"""
        freq = 110 + (coherence * (963 - 110))  # Linear map
        
        closest_emotion = 'Neutral'
        closest_dist = float('inf')
        
        for emotion, emotion_freq in self.EMOTIONAL_FREQUENCIES.items():
            dist = abs(freq - emotion_freq)
            if dist < closest_dist:
                closest_dist = dist
                closest_emotion = emotion
        
        return closest_emotion, freq
    
    def evaluate(self) -> Dict[str, Any]:
        """Evaluate current emotional state from bus data"""
        
        # Read from other systems
        master_eq = BUS.read('MasterEquation')
        lighthouse = BUS.read('Lighthouse')
        checked_at = time.time()
        master_ready, master_reason, master_source = _state_provenance(
            master_eq,
            checked_at,
        )
        lighthouse_ready, lighthouse_reason, lighthouse_source = _state_provenance(
            lighthouse,
            checked_at,
        )
        if not master_ready or not lighthouse_ready:
            reason = (
                f"master_equation:{master_reason}"
                if not master_ready
                else f"lighthouse:{lighthouse_reason}"
            )
            BUS.publish(
                SystemState(
                    system_name=self.NAME,
                    timestamp=checked_at,
                    ready=False,
                    signal="HOLD",
                    data={
                        "truth_status": "no_data",
                        "no_data_reason": reason,
                        "provider_id": "binance",
                        "source_id": "rainbow:hnc+lighthouse",
                        "source_timestamp": None,
                        "received_at": checked_at,
                    },
                )
            )
            return {
                "emotion": None,
                "frequency": None,
                "love_alignment": None,
                "coherence": None,
                "signal": "HOLD",
                "truth_status": "no_data",
                "no_data_reason": reason,
                "source_timestamp": None,
                "received_at": checked_at,
                "action_eligible": False,
            }

        coherence = (master_eq.coherence + lighthouse.coherence) / 2
        
        emotion, freq = self.get_emotional_state(coherence)
        
        # 528 Hz = LOVE = best state
        love_distance = abs(freq - 528)
        love_alignment = max(
            0.0,
            1.0 - (love_distance / 400),
        )
        
        # Signal based on emotional state
        if emotion in ['LOVE', 'Harmony', 'Connection', 'Flow', 'Awakening', 'Clarity', 'Intuition', 'Awe']:
            signal = 'BUY'  # Positive emotions = bullish
        elif emotion in ['Anger', 'Fear', 'Frustration', 'Doubt', 'Worry']:
            signal = 'SELL'  # Negative emotions = bearish
        else:
            signal = 'NEUTRAL'
        
        received_at = time.time()
        source_timestamp = min(master_source, lighthouse_source)
        provenance = {
            "truth_status": "real_derived",
            "provider_id": "binance",
            "source_id": "rainbow:hnc+lighthouse",
            "source_timestamp": source_timestamp,
            "received_at": received_at,
            "emotion": emotion,
            "frequency": freq,
            "vow": self.THE_VOW,
            "generated": False,
        }
        BUS.publish(
            SystemState(
                system_name=self.NAME,
                timestamp=received_at,
                ready=True,
                coherence=love_alignment,
                confidence=coherence,
                signal=signal,
                data=provenance,
            )
        )
        
        return {
            'emotion': emotion,
            'frequency': freq,
            'love_alignment': love_alignment,
            'coherence': coherence,
            'signal': signal,
            'truth_status': 'real_derived',
            'source_timestamp': source_timestamp,
            'received_at': received_at,
            'action_eligible': True,
        }

# ═══════════════════════════════════════════════════════════════════════════
# SYSTEM 5: DECISION FUSION (Consensus Engine)
# ═══════════════════════════════════════════════════════════════════════════

class DecisionFusionSystem:
    """
    Fuses signals from all systems to make final trading decision.
    
    "Each system reads and reassures the next."
    """
    
    NAME = "DecisionFusion"
    
    REQUIRED_SYSTEMS = ['DataIngestion', 'Lighthouse', 'MasterEquation', 'RainbowBridge']
    
    def __init__(self):
        self.weights = {
            'MasterEquation': 0.35,
            'Lighthouse': 0.30,
            'RainbowBridge': 0.20,
            'DataIngestion': 0.15,
        }

    def _no_data(self, reason: str, received_at: float) -> Dict[str, Any]:
        payload = {
            "decision": "HOLD",
            "reason": reason,
            "truth_status": "no_data",
            "no_data_reason": reason,
            "provider_id": "binance",
            "source_id": "decision-fusion:hnc",
            "source_timestamp": None,
            "received_at": received_at,
            "action_eligible": False,
        }
        BUS.publish(
            SystemState(
                system_name=self.NAME,
                timestamp=received_at,
                ready=False,
                signal="HOLD",
                data=dict(payload),
            )
        )
        return payload
    
    def evaluate(self) -> Dict[str, Any]:
        """
        Fuse all system signals into final decision.
        
        Requires consensus from all systems.
        """
        states = BUS.read_all()
        checked_at = time.time()
        source_timestamps: List[float] = []

        for sys_name in self.REQUIRED_SYSTEMS:
            if sys_name not in states:
                return self._no_data(f"{sys_name} not reporting", checked_at)
            eligible, reason, source_timestamp = _state_provenance(
                states[sys_name],
                checked_at,
            )
            if not eligible:
                return self._no_data(
                    f"{sys_name} provenance ineligible:{reason}",
                    checked_at,
                )
            if states[sys_name].signal not in {"BUY", "SELL", "NEUTRAL"}:
                return self._no_data(
                    f"{sys_name} signal ineligible",
                    checked_at,
                )
            source_timestamps.append(source_timestamp)
        
        # Compute weighted score
        buy_score = 0.0
        sell_score = 0.0
        total_coherence = 0.0
        
        for sys_name, weight in self.weights.items():
            state = states[sys_name]
            total_coherence += state.coherence * weight
            
            if state.signal == 'BUY':
                buy_score += weight * state.confidence
            elif state.signal == 'SELL':
                sell_score += weight * state.confidence
        
        # Determine final decision
        if buy_score > sell_score and buy_score > 0.4:
            decision = 'BUY'
            confidence = buy_score
        elif sell_score > buy_score and sell_score > 0.4:
            decision = 'SELL'
            confidence = sell_score
        else:
            decision = 'HOLD'
            confidence = 1.0 - abs(buy_score - sell_score)
        
        received_at = time.time()
        source_timestamp = min(source_timestamps)
        provenance = {
            "truth_status": "real_derived",
            "provider_id": "binance",
            "source_id": "decision-fusion:hnc",
            "source_timestamp": source_timestamp,
            "received_at": received_at,
            "buy_score": buy_score,
            "sell_score": sell_score,
            "system_votes": {
                name: states[name].signal for name in self.REQUIRED_SYSTEMS
            },
            "generated": False,
        }
        BUS.publish(
            SystemState(
                system_name=self.NAME,
                timestamp=received_at,
                ready=True,
                coherence=total_coherence,
                confidence=confidence,
                signal=decision,
                data=provenance,
            )
        )
        
        return {
            'decision': decision,
            'confidence': confidence,
            'coherence': total_coherence,
            'buy_score': buy_score,
            'sell_score': sell_score,
            'truth_status': 'real_derived',
            'source_timestamp': source_timestamp,
            'received_at': received_at,
            'action_eligible': decision in {'BUY', 'SELL'},
        }

# ═══════════════════════════════════════════════════════════════════════════
# SYSTEM 6: ELEPHANT MEMORY (Trade Persistence)
# ═══════════════════════════════════════════════════════════════════════════

class ElephantMemorySystem:
    """
    Persists trade history with cooldowns and blacklisting.
    "The elephant never forgets."
    """
    
    NAME = "ElephantMemory"
    
    def __init__(self, filepath: str = 'elephant_memory.json'):
        self.filepath = filepath
        self.symbols: Dict[str, dict] = {}
        self.cooldown_minutes = 15
        self.loss_streak_limit = 3
    
    def load(self) -> bool:
        self.symbols = {}
        try:
            with open(self.filepath, 'r') as f:
                raw = json.load(f)
        except (OSError, ValueError, TypeError):
            return False
        if not isinstance(raw, dict):
            return False

        rebuilt: Dict[str, Dict[str, Any]] = {}
        for symbol, stored in raw.items():
            if not isinstance(symbol, str) or not isinstance(stored, dict):
                continue
            receipts = stored.get("learning_receipts")
            if not isinstance(receipts, list) or not receipts:
                continue
            ordered = sorted(
                receipts,
                key=lambda receipt: (
                    (
                        _finite_number(
                            receipt.get("source_timestamp"),
                            positive=True,
                        )
                        or float("inf")
                    )
                    if isinstance(receipt, dict)
                    else float("inf")
                ),
            )
            normalised_receipts: List[Dict[str, Any]] = []
            wins = 0
            losses = 0
            total_profit = 0.0
            loss_streak = 0
            blacklisted = False
            valid = True
            for receipt in ordered:
                if not isinstance(receipt, dict):
                    valid = False
                    break
                profit = _finite_number(receipt.get("realized_profit"))
                side = receipt.get("side")
                if (
                    profit is None
                    or not isinstance(side, str)
                    or not self._learning_receipt_is_eligible(
                        symbol,
                        profit,
                        side,
                        receipt,
                        require_current=False,
                    )
                ):
                    valid = False
                    break
                normalised_receipts.append(
                    self._normalised_learning_receipt(receipt)
                )
                total_profit += profit
                if profit >= 0:
                    wins += 1
                    loss_streak = 0
                else:
                    losses += 1
                    loss_streak += 1
                    if loss_streak >= self.loss_streak_limit:
                        blacklisted = True
            if not valid or not normalised_receipts:
                continue
            rebuilt[symbol] = {
                "trades": len(normalised_receipts),
                "wins": wins,
                "losses": losses,
                "profit": total_profit,
                "last_trade": normalised_receipts[-1]["source_timestamp"],
                "loss_streak": loss_streak,
                "blacklisted": blacklisted,
                "learning_receipts": normalised_receipts,
            }
        self.symbols = rebuilt
        return bool(rebuilt)
    
    def save(self):
        with open(self.filepath, 'w') as f:
            json.dump(self.symbols, f, indent=2)
    
    @staticmethod
    def _learning_receipt_is_eligible(
        symbol: str,
        profit: float,
        side: str,
        receipt: Any,
        *,
        require_current: bool = True,
    ) -> bool:
        if not isinstance(receipt, dict):
            return False
        if receipt.get("truth_status") != "real_observed":
            return False
        if receipt.get("generated") is not False:
            return False
        if receipt.get("provider_id") != "binance":
            return False
        if str(receipt.get("status")).upper() != "FILLED":
            return False
        if str(receipt.get("symbol")).upper() != symbol.upper():
            return False
        if str(receipt.get("side")).upper() != side.upper():
            return False
        if not receipt.get("order_id") or not receipt.get("trade_id"):
            return False
        received_at = _finite_number(receipt.get("received_at"), positive=True)
        if received_at is None:
            return False
        if require_current:
            observed_at = _fresh_source_timestamp(
                receipt.get("source_timestamp"),
                time.time(),
            )
        else:
            observed_at = _finite_number(
                receipt.get("source_timestamp"),
                positive=True,
            )
        if observed_at is None:
            return False
        provider_delay = received_at - observed_at
        if (
            provider_delay < -PROVIDER_CLOCK_FUTURE_TOLERANCE_SECONDS
            or provider_delay > MARKET_DATA_MAX_AGE_SECONDS
        ):
            return False
        if math.isclose(
            observed_at,
            received_at,
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            return False
        if receipt.get("accounting_status") != "complete":
            return False
        realised_profit = _finite_number(receipt.get("realized_profit"))
        fee_total = _finite_number(receipt.get("fee_total"), nonnegative=True)
        filled_quantity = _finite_number(
            receipt.get("filled_quantity"),
            positive=True,
        )
        filled_notional = _finite_number(
            receipt.get("filled_notional"),
            positive=True,
        )
        if (
            realised_profit is None
            or fee_total is None
            or filled_quantity is None
            or filled_notional is None
        ):
            return False
        fee_asset = receipt.get("fee_asset")
        if not isinstance(fee_asset, str) or not fee_asset.strip():
            return False
        return math.isclose(realised_profit, profit, rel_tol=1e-9, abs_tol=1e-12)

    @staticmethod
    def _normalised_learning_receipt(
        receipt: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "truth_status": "real_observed",
            "generated": False,
            "provider_id": "binance",
            "status": "FILLED",
            "symbol": str(receipt["symbol"]).upper(),
            "side": str(receipt["side"]).upper(),
            "order_id": str(receipt["order_id"]),
            "trade_id": str(receipt["trade_id"]),
            "source_timestamp": float(receipt["source_timestamp"]),
            "received_at": float(receipt["received_at"]),
            "accounting_status": "complete",
            "realized_profit": float(receipt["realized_profit"]),
            "fee_total": float(receipt["fee_total"]),
            "fee_asset": str(receipt["fee_asset"]).upper(),
            "filled_quantity": float(receipt["filled_quantity"]),
            "filled_notional": float(receipt["filled_notional"]),
        }

    def record_trade(
        self,
        symbol: str,
        profit: float,
        side: str,
        *,
        execution_receipt: Optional[Dict[str, Any]] = None,
    ) -> bool:
        profit_value = _finite_number(profit)
        if profit_value is None or not self._learning_receipt_is_eligible(
            symbol,
            profit_value,
            side,
            execution_receipt,
        ):
            return False
        receipt_source_timestamp = float(execution_receipt["source_timestamp"])
        receipt_received_at = float(execution_receipt["received_at"])
        learning_receipt = self._normalised_learning_receipt(execution_receipt)
        if symbol not in self.symbols:
            self.symbols[symbol] = {
                'trades': 0, 'wins': 0, 'losses': 0,
                'profit': 0.0, 'last_trade': 0, 'loss_streak': 0,
                'blacklisted': False, 'learning_receipts': []
            }
        
        s = self.symbols[symbol]
        s['trades'] += 1
        s['profit'] += profit_value
        s['last_trade'] = receipt_source_timestamp
        s['learning_receipts'].append(learning_receipt)
        
        if profit_value >= 0:
            s['wins'] += 1
            s['loss_streak'] = 0
        else:
            s['losses'] += 1
            s['loss_streak'] += 1
            if s['loss_streak'] >= self.loss_streak_limit:
                s['blacklisted'] = True
        
        self.save()
        
        # Publish to bus
        BUS.publish(SystemState(
            system_name=self.NAME,
            timestamp=receipt_received_at,
            ready=True,
            coherence=self.get_overall_win_rate(),
            confidence=1.0,
            signal="NEUTRAL",
            data={
                "truth_status": "real_derived",
                "provider_id": "binance",
                "source_id": f"elephant:{execution_receipt['order_id']}",
                "source_timestamp": receipt_source_timestamp,
                "received_at": receipt_received_at,
                "last_trade": symbol,
                "profit": profit_value,
                "generated": False,
            },
        ))
        return True
    
    def should_avoid(self, symbol: str) -> bool:
        if symbol not in self.symbols:
            return False
        s = self.symbols[symbol]
        if s.get('blacklisted'):
            return True
        last_trade = _finite_number(s.get("last_trade"), positive=True)
        if last_trade is None:
            return True
        if time.time() - last_trade < self.cooldown_minutes * 60:
            return True
        return False
    
    def get_overall_win_rate(self) -> Optional[float]:
        wins: List[float] = []
        trades: List[float] = []
        for state in self.symbols.values():
            state_wins = _finite_number(state.get("wins"), nonnegative=True)
            state_trades = _finite_number(state.get("trades"), nonnegative=True)
            if state_wins is None or state_trades is None or state_wins > state_trades:
                return None
            wins.append(state_wins)
            trades.append(state_trades)
        total_wins = sum(wins)
        total_trades = sum(trades)
        if total_trades <= 0:
            return None
        return total_wins / total_trades

# ═══════════════════════════════════════════════════════════════════════════
# UNIFIED ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════

class UnifiedOrchestrator:
    """
    The central brain that coordinates all systems.
    
    "Each system reads and reassures the next. Each is a piece to a big puzzle."
    """
    
    def __init__(
        self,
        dry_run: bool = False,
        *,
        client: Optional["BinanceClient"] = None,
        memory_filepath: str = "elephant_memory.json",
    ):
        self.dry_run = dry_run
        self.client = client
        
        # Initialize all systems
        self.data = DataIngestionSystem(self.client)
        self.lighthouse = LighthouseSystem(self.data)
        self.master_eq = MasterEquationSystem(self.data)
        self.rainbow = RainbowBridgeSystem()
        self.fusion = DecisionFusionSystem()
        self.memory = ElephantMemorySystem(memory_filepath)
        
        self.positions = {}
        self.total_profit: Optional[float] = None
        self.trade_count = 0
    
    def get_tradeable_symbols(self) -> List[str]:
        """Get BTC pairs we can trade (TRD_GRP_039)"""
        symbols = []
        for symbol in self.data.ticker_cache.keys():
            if symbol.endswith('BTC'):
                ticker = self.data.get_ticker(symbol)
                if ticker is not None and ticker["quoteVolume"] > 1.0:
                    symbols.append(symbol)
        return sorted(
            symbols,
            key=lambda ticker_symbol: self.data.ticker_cache[ticker_symbol]["quoteVolume"],
            reverse=True,
        )
    
    def display_bus_status(self):
        """Show current state of all systems on the bus"""
        states = BUS.read_all()
        
        logger.info("\n" + "═" * 70)
        logger.info("📡 UNIFIED BUS STATUS")
        logger.info("═" * 70)
        
        for name, state in states.items():
            status = "✅" if state.ready else "❌"
            coherence = (
                f"{state.coherence:.3f}"
                if state.coherence is not None
                else "no_data"
            )
            confidence = (
                f"{state.confidence:.3f}"
                if state.confidence is not None
                else "no_data"
            )
            logger.info(
                f"  {status} {name:20} | Γ={coherence} | "
                f"signal={state.signal:8} | conf={confidence}"
            )
        
        logger.info("═" * 70)
    
    def run_cycle(self) -> Dict[str, Any]:
        """
        Run one complete cycle through all systems.
        
        Flow:
        1. DataIngestion → fetch data
        2. Lighthouse → compute metrics
        3. MasterEquation → compute Λ
        4. RainbowBridge → emotional state
        5. DecisionFusion → final decision
        6. Execute trade if consensus
        """
        
        # Step 1: Data Ingestion
        data_receipt = self.data.update()
        if data_receipt["truth_status"] != "real_observed":
            return {
                "action": "HOLD",
                "truth_status": "no_data",
                "no_data_reason": data_receipt["no_data_reason"],
                "provider_id": "binance",
                "source_id": BINANCE_TICKER_ENDPOINT,
                "source_timestamp": None,
                "received_at": time.time(),
                "action_eligible": False,
            }
        
        # Get tradeable symbols
        symbols = self.get_tradeable_symbols()[:20]
        
        if not symbols:
            logger.warning("No tradeable symbols found")
            return {
                "action": "HOLD",
                "truth_status": "no_data",
                "no_data_reason": "no_complete_tradeable_btc_tickers",
                "provider_id": "binance",
                "source_id": BINANCE_TICKER_ENDPOINT,
                "source_timestamp": data_receipt["source_timestamp"],
                "received_at": time.time(),
                "action_eligible": False,
            }
        
        # Step 2: Lighthouse Metrics
        lighthouse_results = self.lighthouse.evaluate(symbols)
        
        # Step 3: Master Equation
        master_results = self.master_eq.evaluate(symbols)
        
        # Step 4: Rainbow Bridge
        rainbow_result = self.rainbow.evaluate()
        
        # Step 5: Decision Fusion
        fusion_result = self.fusion.evaluate()
        
        # Display bus status
        self.display_bus_status()
        
        # Step 6: Execute if consensus
        if fusion_result["truth_status"] != "real_derived":
            return {
                "action": "HOLD",
                "truth_status": "no_data",
                "no_data_reason": fusion_result["no_data_reason"],
                "provider_id": "binance",
                "source_id": "decision-fusion:hnc",
                "source_timestamp": None,
                "received_at": time.time(),
                "action_eligible": False,
            }
        decision = fusion_result['decision']
        confidence = fusion_result['confidence']
        coherence = fusion_result['coherence']
        
        logger.info(f"\n🎯 FUSION DECISION: {decision} | Confidence: {confidence:.3f} | Coherence: {coherence:.3f}")
        logger.info(f"💜 Emotional State: {rainbow_result['emotion']} ({rainbow_result['frequency']:.1f} Hz)")
        
        if decision != 'HOLD' and confidence > 0.6 and coherence > 0.5:
            # Find best symbol to trade
            best_symbol = None
            best_score: Optional[float] = None
            
            for symbol in symbols:
                if self.memory.should_avoid(symbol):
                    continue
                
                lh = lighthouse_results.get(symbol)
                me = master_results.get(symbol)
                if (
                    lh is None
                    or me is None
                    or not lh["action_eligible"]
                    or not me["action_eligible"]
                ):
                    continue

                score = lh["L"] * 0.5 + me["Lambda"] * 0.5
                
                if best_score is None or score > best_score:
                    best_score = score
                    best_symbol = symbol
            
            if best_symbol:
                logger.info(
                    "\nINTENT ONLY: %s %s | Score: %.3f",
                    decision,
                    best_symbol,
                    best_score,
                )
                received_at = time.time()
                return {
                    'action': 'NOT_SUBMITTED',
                    'decision': decision,
                    'symbol': best_symbol,
                    'score': best_score,
                    'confidence': confidence,
                    'coherence': coherence,
                    'truth_status': 'not_submitted',
                    'submission_status': 'not_submitted',
                    'no_data_reason': 'execution_adapter_not_implemented',
                    'provider_id': 'binance',
                    'source_id': 'decision-fusion:hnc',
                    'source_timestamp': fusion_result['source_timestamp'],
                    'received_at': received_at,
                    'action_eligible': True,
                }

            return {
                "action": "HOLD",
                "truth_status": "no_data",
                "no_data_reason": "no_symbol_with_complete_hnc_evidence",
                "provider_id": "binance",
                "source_id": "decision-fusion:hnc",
                "source_timestamp": fusion_result["source_timestamp"],
                "received_at": time.time(),
                "action_eligible": False,
            }

        return {
            "action": "HOLD",
            "decision": decision,
            "confidence": confidence,
            "coherence": coherence,
            "truth_status": "real_derived",
            "provider_id": "binance",
            "source_id": "decision-fusion:hnc",
            "source_timestamp": fusion_result["source_timestamp"],
            "received_at": time.time(),
            "action_eligible": False,
        }
    
    def run(self, duration_sec: int = 3600):
        """Run the unified orchestrator"""
        
        logger.info("""
╔════════════════════════════════════════════════════════════════════════════════╗
║                    🌊 AUREON UNIFIED ORCHESTRATOR 🌊                           ║
╠════════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║   "Each system reads and reassures the next. Each is a piece to a big puzzle."║
║                                                                                ║
║   SYSTEMS:                                                                     ║
║     📡 DataIngestion   → Fetches market data from Binance                      ║
║     🔦 Lighthouse      → Computes |Q| and G_eff metrics                        ║
║     🌊 MasterEquation  → Λ(t) = S(t) + O(t) + E(t)                             ║
║     🌈 RainbowBridge   → Emotional frequency mapping (528 Hz = LOVE)           ║
║     🧠 DecisionFusion  → Consensus-based trade decisions                       ║
║     🐘 ElephantMemory  → Trade persistence with cooldowns                      ║
║                                                                                ║
║   COMMUNICATION:                                                               ║
║     All systems publish to UnifiedBus                                          ║
║     All systems read from UnifiedBus                                           ║
║     Consensus required for trade execution                                     ║
║                                                                                ║
╚════════════════════════════════════════════════════════════════════════════════╝
""")
        
        start = time.time()
        cycle = 0
        
        while time.time() - start < duration_sec:
            cycle += 1
            logger.info(f"\n{'─'*70}")
            logger.info(f"🔄 CYCLE {cycle}")
            logger.info(f"{'─'*70}")
            
            try:
                result = self.run_cycle()
                
                if (
                    result.get("truth_status") == "real_observed"
                    and result.get("status") == "FILLED"
                    and result.get("order_id")
                    and result.get("trade_id")
                ):
                    self.trade_count += 1
                    logger.info(f"✅ Trade #{self.trade_count}: {result['action']} {result['symbol']}")
                
            except Exception as e:
                logger.error(f"❌ Cycle error: {e}")
            
            time.sleep(10)  # 10 second cycles
        
        logger.info(f"\n🏁 Session complete. Trades executed: {self.trade_count}")

def main():
    _runtime_bootstrap()
    from aureon.exchanges.binance_client import get_binance_client
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--duration', type=int, default=300)
    args = parser.parse_args()
    
    orchestrator = UnifiedOrchestrator(
        dry_run=args.dry_run,
        client=get_binance_client(),
    )
    orchestrator.memory.load()
    orchestrator.run(duration_sec=args.duration)

if __name__ == "__main__":
    main()
