#!/usr/bin/env python3
"""
🌍⚡ COINAPI ANOMALY DETECTOR - DATA TRUTH ENGINE ⚡🌍
═══════════════════════════════════════════════════════════════

Cross-validates market data from CoinAPI with our internal feeds.
Detects anomalies, discrepancies, and hidden signals in the data.
Uses anomalies to refine our own algorithms and discover the "real story".

CoinAPI provides aggregated data from 300+ exchanges:
- OHLCV data (trades, quotes, order books)
- Real-time and historical market data
- Exchange metadata and status

We use this to:
1. Detect price manipulation or wash trading
2. Find arbitrage opportunities across exchanges
3. Identify data feed latencies and frontrunning
4. Validate our own data quality
5. Discover hidden liquidity patterns

Gary Leckey & GitHub Copilot | November 2025
"The Truth is in the Anomalies"
"""

import os
import builtins
import math
import sys
import time
import requests
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import deque
from enum import Enum
import statistics

# ═══════════════════════════════════════════════════════════════
# COINAPI CONFIGURATION
# ═══════════════════════════════════════════════════════════════

COINAPI_BASE_URL = "https://rest.coinapi.io/v1"
COINAPI_API_KEY = os.getenv('COINAPI_KEY', '')  # Set in .env
COINAPI_QUOTE_TTL_SECONDS = max(
    1.0,
    float(os.getenv("COINAPI_QUOTE_TTL_SECONDS", "120") or 120),
)
COINAPI_FUTURE_SKEW_SECONDS = 300.0
COINAPI_TRADE_TTL_SECONDS = max(
    1.0,
    float(os.getenv("COINAPI_TRADE_TTL_SECONDS", "900") or 900),
)


def _console_print(message: Any = "") -> None:
    """Write Unicode diagnostics without failing on legacy Windows consoles."""
    try:
        builtins.print(message)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        rendered = str(message).encode(encoding, errors="replace").decode(
            encoding,
            errors="replace",
        )
        sys.stdout.write(rendered + "\n")

# Anomaly detection thresholds
ANOMALY_THRESHOLDS = {
    'PRICE_SPREAD': 0.02,        # 2% price difference is anomalous
    'VOLUME_SPIKE': 3.0,         # 3x average volume
    'LATENCY_MS': 500,           # 500ms latency is suspicious
    'ORDERBOOK_IMBALANCE': 0.7,  # 70/30 bid/ask ratio
    'WASH_TRADE_RATIO': 0.15,    # 15% wash trading indicator
    'FRONTRUN_WINDOW_MS': 100,   # 100ms frontrunning window
}

# Prime-based confidence scoring
PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]


def _finite_number(value: Any, *, positive: bool = False, nonnegative: bool = False) -> Optional[float]:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    if positive and number <= 0:
        return None
    if nonnegative and number < 0:
        return None
    return number


def _provider_datetime(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _is_fresh_provider_datetime(value: Optional[datetime], *, now: Optional[datetime] = None) -> bool:
    if value is None or value.tzinfo is None:
        return False
    received_at = now or datetime.now(timezone.utc)
    age = (received_at - value).total_seconds()
    return -COINAPI_FUTURE_SKEW_SECONDS <= age <= COINAPI_QUOTE_TTL_SECONDS


def _is_fresh_trade_datetime(value: Optional[datetime], *, now: Optional[datetime] = None) -> bool:
    if value is None or value.tzinfo is None:
        return False
    received_at = now or datetime.now(timezone.utc)
    age = (received_at - value).total_seconds()
    return -COINAPI_FUTURE_SKEW_SECONDS <= age <= COINAPI_TRADE_TTL_SECONDS


def _link_runtime_system() -> None:
    """Join the baton only from an explicit live runtime entrypoint."""
    from aureon.core.aureon_baton_link import link_system

    link_system(__name__)


class AnomalyType(Enum):
    """Types of market data anomalies"""
    PRICE_MANIPULATION = "💰 Price Manipulation"
    WASH_TRADING = "🔄 Wash Trading"
    LATENCY_ARBITRAGE = "⚡ Latency Arbitrage"
    ORDERBOOK_SPOOFING = "📊 Orderbook Spoofing"
    VOLUME_INFLATION = "📈 Volume Inflation"
    EXCHANGE_OUTAGE = "🚨 Exchange Outage"
    FRONTRUNNING = "🎯 Frontrunning Detected"
    LIQUIDITY_DRAIN = "💧 Liquidity Drain"
    CROSS_EXCHANGE_SPREAD = "🌐 Cross-Exchange Spread"


@dataclass
class MarketAnomaly:
    """Detected market anomaly"""
    anomaly_type: AnomalyType
    symbol: str
    exchange: str
    timestamp: datetime
    severity: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    description: str
    evidence: Dict[str, Any]
    recommendation: str
    truth_status: str
    source_id: str
    source_timestamp: datetime
    received_at: datetime
    generated_values: bool = False
    eligible_for_learning: bool = True
    eligible_for_external_action: bool = False
    
    # Refinement data
    expected_value: Optional[float] = None
    actual_value: Optional[float] = None
    deviation_pct: Optional[float] = None
    
    def to_dict(self) -> Dict:
        return {
            'type': self.anomaly_type.value,
            'symbol': self.symbol,
            'exchange': self.exchange,
            'timestamp': self.timestamp.isoformat(),
            'severity': self.severity,
            'confidence': self.confidence,
            'description': self.description,
            'evidence': self.evidence,
            'recommendation': self.recommendation,
            'truth_status': self.truth_status,
            'source_id': self.source_id,
            'source_timestamp': self.source_timestamp.isoformat(),
            'received_at': self.received_at.isoformat(),
            'generated_values': self.generated_values,
            'eligible_for_learning': self.eligible_for_learning,
            'eligible_for_external_action': self.eligible_for_external_action,
            'expected': self.expected_value,
            'actual': self.actual_value,
            'deviation': self.deviation_pct,
        }


@dataclass
class ExchangeDataPoint:
    """Single data point from an exchange via CoinAPI"""
    exchange_id: str
    symbol: str
    price: float
    volume_24h: Optional[float]
    bid: float
    ask: float
    timestamp: datetime
    received_at: datetime
    source_id: str
    truth_status: str = "real_derived"
    generated_values: bool = False
    latency_ms: Optional[float] = None
    
    def spread_pct(self) -> Optional[float]:
        """Calculate bid-ask spread percentage"""
        if self.bid <= 0:
            return None
        return ((self.ask - self.bid) / self.bid) * 100


def _eligible_exchange_points(data_points: List[ExchangeDataPoint]) -> List[ExchangeDataPoint]:
    """Return only fresh, provider-backed quote observations."""
    received_at = datetime.now(timezone.utc)
    eligible: List[ExchangeDataPoint] = []
    for point in data_points:
        if not isinstance(point, ExchangeDataPoint):
            continue
        if point.truth_status not in {"real_observed", "real_derived"} or point.generated_values:
            continue
        if not point.source_id or not _is_fresh_provider_datetime(point.timestamp, now=received_at):
            continue
        if (
            _finite_number(point.price, positive=True) is None
            or _finite_number(point.bid, positive=True) is None
            or _finite_number(point.ask, positive=True) is None
            or point.ask <= point.bid
        ):
            continue
        eligible.append(point)
    return eligible


def _validated_book_side(raw_levels: Any) -> Optional[List[Dict[str, float]]]:
    if not isinstance(raw_levels, list) or not raw_levels:
        return None
    levels: List[Dict[str, float]] = []
    for raw_level in raw_levels[:10]:
        if not isinstance(raw_level, dict):
            return None
        price = _finite_number(raw_level.get("price"), positive=True)
        size = _finite_number(raw_level.get("size"), positive=True)
        if price is None or size is None:
            return None
        levels.append({"price": price, "size": size})
    return levels or None


class CoinAPIClient:
    """
    CoinAPI REST client for fetching multi-exchange data.
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or COINAPI_API_KEY
        self.base_url = COINAPI_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            'X-CoinAPI-Key': self.api_key,
            'Accept': 'application/json',
        })
        self.last_status_code: Optional[int] = None
        self.last_error_text: Optional[str] = None
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests
        
        # Cache
        self.exchange_cache = {}
        self.symbol_cache = {}
        
    def _rate_limit(self):
        """Enforce rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
    
    def _request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make API request with error handling"""
        if not self.api_key:
            return None
        
        self._rate_limit()
        
        try:
            url = f"{self.base_url}/{endpoint}"
            response = self.session.get(url, params=params, timeout=10)
            self.last_status_code = int(getattr(response, "status_code", 0) or 0)
            
            if response.status_code == 200:
                self.last_error_text = None
                return response.json()
            elif response.status_code == 429:
                self.last_error_text = str(getattr(response, "text", "") or "")
                _console_print("⚠️  CoinAPI rate limit hit")
                return None
            else:
                self.last_error_text = str(getattr(response, "text", "") or "")
                snippet = self.last_error_text[:200].replace("\n", " ")
                _console_print(f"⚠️  CoinAPI error: {response.status_code} ({snippet})")
                return None
        except Exception as e:
            self.last_status_code = None
            self.last_error_text = str(e)
            _console_print(f"⚠️  CoinAPI request failed: {e}")
            return None
    
    def get_exchanges(self) -> List[Dict]:
        """Get list of all exchanges"""
        if 'exchanges' in self.exchange_cache:
            return self.exchange_cache['exchanges']
        
        data = self._request('exchanges')
        if data:
            self.exchange_cache['exchanges'] = data
            return data
        return []
    
    def get_current_rate(self, asset_id_base: str, asset_id_quote: str) -> Optional[Dict]:
        """Get current exchange rate"""
        endpoint = f"exchangerate/{asset_id_base}/{asset_id_quote}"
        return self._request(endpoint)
    
    def get_ohlcv_latest(self, symbol_id: str, period: str = "1MIN", limit: int = 100) -> List[Dict]:
        """Get latest OHLCV data"""
        endpoint = f"ohlcv/{symbol_id}/latest"
        params = {'period_id': period, 'limit': limit}
        data = self._request(endpoint, params)
        return data if data else []

    def get_ohlcv_history(
        self,
        symbol_id: str,
        period: str = "1MIN",
        time_start: str | None = None,
        time_end: str | None = None,
        limit: int = 10000,
    ) -> List[Dict]:
        """Get historical OHLCV data (CoinAPI /ohlcv/{symbol_id}/history)."""
        endpoint = f"ohlcv/{symbol_id}/history"
        params: Dict[str, Any] = {'period_id': period, 'limit': limit}
        if time_start:
            params['time_start'] = time_start
        if time_end:
            params['time_end'] = time_end
        data = self._request(endpoint, params)
        return data if data else []
    
    def get_quotes_current(self, symbol_id: str = None) -> List[Dict]:
        """Get current quotes (bid/ask)"""
        endpoint = "quotes/current"
        params = {'filter_symbol_id': symbol_id} if symbol_id else {}
        data = self._request(endpoint, params)
        return data if data else []
    
    def get_orderbook_current(self, symbol_id: str, limit_levels: int = 20) -> Optional[Dict]:
        """Get current orderbook"""
        endpoint = f"orderbooks/{symbol_id}/current"
        params = {'limit_levels': limit_levels}
        return self._request(endpoint, params)
    
    def get_trades_latest(self, symbol_id: str, limit: int = 100) -> List[Dict]:
        """Get latest trades"""
        endpoint = f"trades/{symbol_id}/latest"
        params = {'limit': limit}
        data = self._request(endpoint, params)
        return data if data else []

    def get_trades_history(
        self,
        symbol_id: str,
        time_start: str | None = None,
        time_end: str | None = None,
        limit: int = 10000,
    ) -> List[Dict]:
        """Get historical trades (CoinAPI /trades/{symbol_id}/history)."""
        endpoint = f"trades/{symbol_id}/history"
        params: Dict[str, Any] = {'limit': limit}
        if time_start:
            params['time_start'] = time_start
        if time_end:
            params['time_end'] = time_end
        data = self._request(endpoint, params)
        return data if data else []

    def get_assets(self) -> List[Dict]:
        """Get the full CoinAPI assets registry."""
        data = self._request("assets")
        return data if data else []

    def get_symbols(self) -> List[Dict]:
        """Get the full CoinAPI symbols registry."""
        data = self._request("symbols")
        return data if data else []


class AnomalyDetector:
    """
    Detects anomalies in CoinAPI data and uses them to refine algorithms.
    """
    
    def __init__(self, coinapi_client: CoinAPIClient):
        self.client = coinapi_client
        
        # Anomaly storage
        self.detected_anomalies: deque = deque(maxlen=1000)
        self.anomaly_history: Dict[str, List[MarketAnomaly]] = {}
        
        # Statistical baselines
        self.price_baselines: Dict[str, deque] = {}
        self.volume_baselines: Dict[str, deque] = {}
        self.spread_baselines: Dict[str, deque] = {}
        
        # Cross-exchange tracking
        self.multi_exchange_cache: Dict[str, List[ExchangeDataPoint]] = {}
        
        # Algorithm refinement metrics
        self.refinement_log: List[Dict] = []
        
    def fetch_multi_exchange_data(self, base_asset: str, quote_asset: str) -> List[ExchangeDataPoint]:
        """
        Fetch price data from multiple exchanges for the same pair.
        This is where we find discrepancies and the "real story".
        """
        data_points = []
        
        # Try to get quotes for this pair across exchanges
        symbol_filter = f"*_{base_asset}_{quote_asset}"
        quotes = self.client.get_quotes_current(symbol_filter)
        
        received_at = datetime.now(timezone.utc)
        for quote in quotes:
            try:
                symbol_id = str(quote.get('symbol_id') or '').strip()
                exchange_id = symbol_id.split('_')[0]
                bid = _finite_number(quote.get('bid'), positive=True)
                ask = _finite_number(quote.get('ask'), positive=True)
                timestamp = _provider_datetime(quote.get('time_exchange'))
                if (
                    not exchange_id
                    or bid is None
                    or ask is None
                    or ask <= bid
                    or not _is_fresh_provider_datetime(timestamp, now=received_at)
                ):
                    continue
                data_points.append(ExchangeDataPoint(
                    exchange_id=exchange_id,
                    symbol=f"{base_asset}/{quote_asset}",
                    price=(bid + ask) / 2.0,
                    volume_24h=None,
                    bid=bid,
                    ask=ask,
                    timestamp=timestamp,
                    received_at=received_at,
                    source_id=f"coinapi_quote:{symbol_id}",
                    truth_status="real_derived",
                    generated_values=False,
                ))
            except (TypeError, ValueError, AttributeError):
                continue
        
        # Cache for later analysis
        key = f"{base_asset}_{quote_asset}"
        self.multi_exchange_cache[key] = data_points
        
        return data_points
    
    def detect_price_manipulation(self, data_points: List[ExchangeDataPoint]) -> List[MarketAnomaly]:
        """
        Detect price manipulation by comparing prices across exchanges.
        Large discrepancies indicate manipulation or wash trading.
        """
        data_points = _eligible_exchange_points(data_points)
        if len(data_points) < 2:
            return []
        
        anomalies = []
        prices = [dp.price for dp in data_points]
        mean_price = statistics.mean(prices)
        std_price = statistics.stdev(prices)
        source_timestamp = min(point.timestamp for point in data_points)
        received_at = max(point.received_at for point in data_points)
        source_ids = sorted({point.source_id for point in data_points})
        
        for dp in data_points:
            deviation = abs(dp.price - mean_price) / mean_price
            
            if deviation > ANOMALY_THRESHOLDS['PRICE_SPREAD']:
                severity = min(1.0, deviation / (ANOMALY_THRESHOLDS['PRICE_SPREAD'] * 2))
                confidence = min(1.0, len(data_points) / 10.0)
                
                anomaly = MarketAnomaly(
                    anomaly_type=AnomalyType.PRICE_MANIPULATION,
                    symbol=dp.symbol,
                    exchange=dp.exchange_id,
                    timestamp=dp.timestamp,
                    severity=severity,
                    confidence=confidence,
                    description=f"Price {deviation:.1%} away from cross-exchange mean",
                    evidence={
                        'exchange_price': dp.price,
                        'mean_price': mean_price,
                        'std_dev': std_price,
                        'num_exchanges': len(data_points),
                        'source_ids': source_ids,
                        'source_timestamp': source_timestamp.isoformat(),
                        'confidence_basis': 'fresh_exchange_count/10',
                        'execution_eligible': False,
                    },
                    recommendation="AVOID" if severity > 0.5 else "CAUTION",
                    truth_status="real_derived",
                    source_id="|".join(source_ids),
                    source_timestamp=source_timestamp,
                    received_at=received_at,
                    generated_values=False,
                    eligible_for_learning=True,
                    eligible_for_external_action=False,
                    expected_value=mean_price,
                    actual_value=dp.price,
                    deviation_pct=deviation * 100,
                )
                
                anomalies.append(anomaly)
        
        return anomalies
    
    def detect_orderbook_spoofing(self, symbol_id: str) -> Optional[MarketAnomaly]:
        """
        Detect orderbook spoofing by analyzing bid/ask imbalance.
        """
        orderbook = self.client.get_orderbook_current(symbol_id)
        if not orderbook:
            return None
        
        try:
            received_at = datetime.now(timezone.utc)
            source_timestamp = _provider_datetime(orderbook.get('time_exchange'))
            bids = _validated_book_side(orderbook.get('bids'))
            asks = _validated_book_side(orderbook.get('asks'))
            if (
                bids is None
                or asks is None
                or not _is_fresh_provider_datetime(source_timestamp, now=received_at)
            ):
                return None

            bid_volume = sum(level['size'] for level in bids)
            ask_volume = sum(level['size'] for level in asks)
            total_volume = bid_volume + ask_volume
            if total_volume <= 0:
                return None

            bid_ratio = bid_volume / total_volume
            if bid_ratio > ANOMALY_THRESHOLDS['ORDERBOOK_IMBALANCE'] or bid_ratio < (1 - ANOMALY_THRESHOLDS['ORDERBOOK_IMBALANCE']):
                severity = abs(bid_ratio - 0.5) * 2
                confidence = min(1.0, (len(bids) + len(asks)) / 20.0)
                return MarketAnomaly(
                    anomaly_type=AnomalyType.ORDERBOOK_SPOOFING,
                    symbol=symbol_id,
                    exchange=symbol_id.split('_')[0],
                    timestamp=source_timestamp,
                    severity=severity,
                    confidence=confidence,
                    description=f"Orderbook imbalance: {bid_ratio:.0%} bids vs {1-bid_ratio:.0%} asks",
                    evidence={
                        'bid_volume': bid_volume,
                        'ask_volume': ask_volume,
                        'bid_ratio': bid_ratio,
                        'top_bid': bids[0],
                        'top_ask': asks[0],
                        'levels_observed': len(bids) + len(asks),
                        'confidence_basis': 'observed_depth_levels/20',
                        'source_timestamp': source_timestamp.isoformat(),
                        'execution_eligible': False,
                    },
                    recommendation="WAIT" if severity > 0.6 else "CAUTION",
                    truth_status="real_derived",
                    source_id=f"coinapi_orderbook:{symbol_id}",
                    source_timestamp=source_timestamp,
                    received_at=received_at,
                    generated_values=False,
                    eligible_for_learning=True,
                    eligible_for_external_action=False,
                    expected_value=0.5,
                    actual_value=bid_ratio,
                    deviation_pct=(bid_ratio - 0.5) * 200,
                )
        except (TypeError, ValueError, AttributeError):
            return None
    
    def detect_wash_trading(self, symbol_id: str) -> Optional[MarketAnomaly]:
        """
        Detect wash trading by analyzing trade patterns.
        Circular trades at similar prices indicate wash trading.
        """
        trades = self.client.get_trades_latest(symbol_id, limit=100)
        if len(trades) < 10:
            return None
        
        try:
            received_at = datetime.now(timezone.utc)
            validated_trades: List[Dict[str, Any]] = []
            for trade in trades:
                if not isinstance(trade, dict):
                    continue
                price = _finite_number(trade.get('price'), positive=True)
                size = _finite_number(trade.get('size'), positive=True)
                source_timestamp = _provider_datetime(trade.get('time_exchange'))
                if (
                    price is None
                    or size is None
                    or not _is_fresh_trade_datetime(source_timestamp, now=received_at)
                ):
                    continue
                validated_trades.append({
                    'price': price,
                    'size': size,
                    'source_timestamp': source_timestamp,
                })

            if len(validated_trades) < 10:
                return None

            price_counts: Dict[float, int] = {}
            for trade in validated_trades:
                rounded = round(trade['price'], 8)
                price_counts[rounded] = price_counts.get(rounded, 0) + 1

            max_repetitions = max(price_counts.values())
            repetition_ratio = max_repetitions / len(validated_trades)
            threshold = ANOMALY_THRESHOLDS['WASH_TRADE_RATIO']
            if repetition_ratio > threshold:
                source_timestamp = min(trade['source_timestamp'] for trade in validated_trades)
                confidence = min(1.0, len(validated_trades) / 100.0)
                return MarketAnomaly(
                    anomaly_type=AnomalyType.WASH_TRADING,
                    symbol=symbol_id,
                    exchange=symbol_id.split('_')[0],
                    timestamp=source_timestamp,
                    severity=min(1.0, repetition_ratio),
                    confidence=confidence,
                    description=f"{repetition_ratio:.0%} of fresh observed trades share one price",
                    evidence={
                        'max_repetitions': max_repetitions,
                        'total_trades': len(validated_trades),
                        'total_observed_volume': sum(trade['size'] for trade in validated_trades),
                        'repetition_ratio': repetition_ratio,
                        'unique_prices': len(price_counts),
                        'confidence_basis': 'fresh_trade_count/100',
                        'source_timestamp': source_timestamp.isoformat(),
                        'execution_eligible': False,
                    },
                    recommendation="REVIEW",
                    truth_status="real_derived",
                    source_id=f"coinapi_trades:{symbol_id}",
                    source_timestamp=source_timestamp,
                    received_at=received_at,
                    generated_values=False,
                    eligible_for_learning=True,
                    eligible_for_external_action=False,
                    expected_value=threshold,
                    actual_value=repetition_ratio,
                    deviation_pct=((repetition_ratio - threshold) / threshold) * 100,
                )
        except (TypeError, ValueError, AttributeError, statistics.StatisticsError):
            return None
    
    def detect_cross_exchange_arbitrage(self, data_points: List[ExchangeDataPoint]) -> List[MarketAnomaly]:
        """
        Detect arbitrage opportunities from price discrepancies.
        These reveal the "real" price vs manipulated prices.
        """
        data_points = _eligible_exchange_points(data_points)
        if len(data_points) < 2:
            return []
        
        anomalies = []
        
        # Find min and max prices
        sorted_points = sorted(data_points, key=lambda x: x.price)
        min_dp = sorted_points[0]
        max_dp = sorted_points[-1]
        
        spread_pct = (max_dp.price - min_dp.price) / min_dp.price
        
        if spread_pct > ANOMALY_THRESHOLDS['PRICE_SPREAD']:
            source_timestamp = min(point.timestamp for point in data_points)
            received_at = max(point.received_at for point in data_points)
            source_ids = sorted({point.source_id for point in data_points})
            anomaly = MarketAnomaly(
                anomaly_type=AnomalyType.CROSS_EXCHANGE_SPREAD,
                symbol=min_dp.symbol,
                exchange=f"{min_dp.exchange_id}→{max_dp.exchange_id}",
                timestamp=source_timestamp,
                severity=min(1.0, spread_pct / (ANOMALY_THRESHOLDS['PRICE_SPREAD'] * 2)),
                confidence=min(1.0, len(data_points) / 10.0),
                description=f"{spread_pct:.2%} observed cross-exchange price spread",
                evidence={
                    'buy_exchange': min_dp.exchange_id,
                    'buy_price': min_dp.price,
                    'sell_exchange': max_dp.exchange_id,
                    'sell_price': max_dp.price,
                    'profit_pct': spread_pct * 100,
                    'source_ids': source_ids,
                    'source_timestamp': source_timestamp.isoformat(),
                    'confidence_basis': 'fresh_exchange_count/10',
                    'fees_transfers_and_fillability_verified': False,
                    'execution_eligible': False,
                },
                recommendation="OBSERVE; REQUIRE LIVE COST AND FILL RECEIPTS BEFORE ACTION",
                truth_status="real_derived",
                source_id="|".join(source_ids),
                source_timestamp=source_timestamp,
                received_at=received_at,
                generated_values=False,
                eligible_for_learning=True,
                eligible_for_external_action=False,
                expected_value=min_dp.price,
                actual_value=max_dp.price,
                deviation_pct=spread_pct * 100,
            )
            anomalies.append(anomaly)
        
        return anomalies
    
    def refine_algorithm(self, anomaly: MarketAnomaly) -> Dict[str, Any]:
        """
        Use detected anomaly to refine our trading algorithms.
        Returns refinement recommendations.
        """
        received_at = datetime.now(timezone.utc)
        freshness_check = (
            _is_fresh_trade_datetime
            if anomaly.anomaly_type == AnomalyType.WASH_TRADING
            else _is_fresh_provider_datetime
        )
        if (
            anomaly.truth_status not in {"real_observed", "real_derived"}
            or anomaly.generated_values
            or not anomaly.eligible_for_learning
            or not anomaly.source_id
            or not freshness_check(anomaly.source_timestamp, now=received_at)
        ):
            return {
                'received_at': received_at.isoformat(),
                'source_timestamp': None,
                'source_id': None,
                'anomaly_type': anomaly.anomaly_type.value,
                'symbol': anomaly.symbol,
                'adjustment': {},
                'truth_status': 'no_data',
                'generated_values': False,
                'eligible_for_learning': False,
                'eligible_for_external_action': False,
                'reason': 'fresh_provider_anomaly_required',
            }

        refinement = {
            'received_at': received_at.isoformat(),
            'source_timestamp': anomaly.source_timestamp.isoformat(),
            'source_id': anomaly.source_id,
            'anomaly_type': anomaly.anomaly_type.value,
            'symbol': anomaly.symbol,
            'adjustment': {},
            'truth_status': 'real_derived',
            'generated_values': False,
            'eligible_for_learning': True,
            'eligible_for_external_action': False,
            'policy_source': 'coinapi_anomaly_refinement_policy',
        }
        
        if anomaly.anomaly_type == AnomalyType.PRICE_MANIPULATION:
            # Increase coherence threshold for this symbol
            refinement['adjustment'] = {
                'coherence_threshold': '+0.1',
                'position_size': '×0.5',
                'reason': 'Price manipulation detected - require higher confidence',
            }
        
        elif anomaly.anomaly_type == AnomalyType.WASH_TRADING:
            # Blacklist symbol temporarily
            refinement['adjustment'] = {
                'blacklist_duration': '1h',
                'position_size': '×0.0',
                'reason': 'Wash trading detected - avoid completely',
            }
        
        elif anomaly.anomaly_type == AnomalyType.ORDERBOOK_SPOOFING:
            # Wait for orderbook to stabilize
            refinement['adjustment'] = {
                'entry_delay': '+60s',
                'position_size': '×0.7',
                'reason': 'Orderbook spoofing - wait for real liquidity',
            }
        
        elif anomaly.anomaly_type == AnomalyType.CROSS_EXCHANGE_SPREAD:
            refinement['adjustment'] = {
                'price_source': 'multi_exchange_mean',
                'external_action': 'blocked_pending_cost_and_fill_receipts',
                'reason': 'Observed spread requires venue-cost and fill validation',
            }
        
        elif anomaly.anomaly_type == AnomalyType.LATENCY_ARBITRAGE:
            latency_ms = _finite_number(anomaly.evidence.get("latency_ms"), nonnegative=True)
            if latency_ms is None:
                refinement.update({
                    'truth_status': 'no_data',
                    'eligible_for_learning': False,
                    'reason': 'observed_latency_required',
                })
                return refinement
            refinement['adjustment'] = {
                'latency_compensation': f'+{latency_ms}ms',
                'position_size': '×0.8',
                'reason': 'High latency detected - adjust timing',
            }

        if not refinement['adjustment']:
            refinement.update({
                'truth_status': 'no_data',
                'eligible_for_learning': False,
                'reason': 'unsupported_anomaly_type',
            })
            return refinement

        self.refinement_log.append(refinement)
        
        return refinement
    
    def analyze_symbol(self, base_asset: str, quote_asset: str) -> Dict[str, Any]:
        """
        Complete anomaly analysis for a symbol.
        Returns all detected anomalies and refinement recommendations.
        """
        _console_print(f"\n🔍 Analyzing {base_asset}/{quote_asset} across exchanges...")
        
        # Fetch multi-exchange data
        received_at = datetime.now(timezone.utc)
        data_points = _eligible_exchange_points(
            self.fetch_multi_exchange_data(base_asset, quote_asset)
        )
        
        if not data_points:
            _console_print("   ⚠️  No data available")
            return {
                'symbol': f"{base_asset}/{quote_asset}",
                'exchanges_analyzed': 0,
                'anomalies': [],
                'refinements': [],
                'mean_price': None,
                'price_std': None,
                'truth_status': 'no_data',
                'source_id': None,
                'source_timestamp': None,
                'received_at': received_at.isoformat(),
                'generated_values': False,
                'eligible_for_learning': False,
                'eligible_for_external_action': False,
                'reason': 'fresh_coinapi_quotes_unavailable',
            }
        
        _console_print(f"   📊 Found data from {len(data_points)} exchanges")
        
        all_anomalies = []
        all_refinements = []
        
        # Detect price manipulation
        price_anomalies = self.detect_price_manipulation(data_points)
        all_anomalies.extend(price_anomalies)
        
        # Detect arbitrage opportunities
        arb_anomalies = self.detect_cross_exchange_arbitrage(data_points)
        all_anomalies.extend(arb_anomalies)
        
        # Store anomalies
        for anomaly in all_anomalies:
            self.detected_anomalies.append(anomaly)
            
            # Refine algorithm based on anomaly
            refinement = self.refine_algorithm(anomaly)
            if refinement.get('truth_status') == 'real_derived':
                all_refinements.append(refinement)

        source_timestamp = min(point.timestamp for point in data_points)
        source_ids = sorted({point.source_id for point in data_points})
        prices = [point.price for point in data_points]
        
        return {
            'symbol': f"{base_asset}/{quote_asset}",
            'exchanges_analyzed': len(data_points),
            'anomalies': [a.to_dict() for a in all_anomalies],
            'refinements': all_refinements,
            'mean_price': statistics.mean(prices),
            'price_std': statistics.stdev(prices) if len(prices) > 1 else None,
            'truth_status': 'real_derived',
            'source_id': '|'.join(source_ids),
            'source_timestamp': source_timestamp.isoformat(),
            'received_at': received_at.isoformat(),
            'generated_values': False,
            'eligible_for_learning': True,
            'eligible_for_external_action': False,
        }
    
    def print_anomaly_report(self, analysis: Dict):
        """Print formatted anomaly report"""
        mean_price = _finite_number(analysis.get('mean_price'), positive=True)
        price_std = _finite_number(analysis.get('price_std'), nonnegative=True)
        mean_display = f"${mean_price:.6f}" if mean_price is not None else "NO DATA"
        std_display = f"${price_std:.6f}" if price_std is not None else "NO DATA"
        _console_print(f"""
╔══════════════════════════════════════════════════════════════════════════╗
║  🌍⚡ COINAPI ANOMALY REPORT: {analysis['symbol']:20s}            ║
╠══════════════════════════════════════════════════════════════════════════╣
║  Exchanges Analyzed: {analysis['exchanges_analyzed']:2d}                                               ║
║  Mean Price: {mean_display:48s}                 ║
║  Price StdDev: {std_display:45s}                 ║
╠══════════════════════════════════════════════════════════════════════════╣""")
        
        if analysis['anomalies']:
            _console_print("║  DETECTED ANOMALIES:                                                     ║")
            _console_print("╠══════════════════════════════════════════════════════════════════════════╣")
            
            for i, anom in enumerate(analysis['anomalies'][:5], 1):
                severity_bar = "█" * int(anom['severity'] * 10) + "░" * (10 - int(anom['severity'] * 10))
                _console_print(f"║  {i}. {anom['type']:30s}                                  ║")
                _console_print(f"║     Severity: {severity_bar} {anom['severity']:.0%}                               ║")
                _console_print(f"║     {anom['description'][:68]:68s} ║")
                _console_print(f"║     → {anom['recommendation']:64s} ║")
                _console_print("╠══════════════════════════════════════════════════════════════════════════╣")
        elif analysis.get('truth_status') == 'no_data':
            _console_print("║  ⚠️  NO DATA - no anomaly conclusion was produced                         ║")
            _console_print("╠══════════════════════════════════════════════════════════════════════════╣")
        else:
            _console_print("║  ✅ No threshold breaches observed in fresh provider data                ║")
            _console_print("╠══════════════════════════════════════════════════════════════════════════╣")
        
        if analysis['refinements']:
            _console_print("║  ALGORITHM REFINEMENTS:                                                  ║")
            _console_print("╠══════════════════════════════════════════════════════════════════════════╣")
            
            for i, ref in enumerate(analysis['refinements'][:3], 1):
                adj = ref['adjustment']
                _console_print(f"║  {i}. {adj.get('reason', 'No reason')[:68]:68s} ║")
                for key, value in adj.items():
                    if key != 'reason':
                        _console_print(f"║     • {key}: {str(value)[:58]:58s} ║")
                _console_print("╠══════════════════════════════════════════════════════════════════════════╣")
        
        _console_print("╚══════════════════════════════════════════════════════════════════════════╝")


# ═══════════════════════════════════════════════════════════════
# LIVE RUNTIME ENTRYPOINT
# ═══════════════════════════════════════════════════════════════

def run_live_anomaly_detection() -> Dict[str, Any]:
    """Run provider-backed anomaly analysis with no substitute data path."""
    api_key = str(os.getenv('COINAPI_KEY') or '').strip()
    if not api_key:
        raise RuntimeError("COINAPI_KEY missing; live anomaly detection unavailable")

    _link_runtime_system()
    client = CoinAPIClient(api_key)
    detector = AnomalyDetector(client)
    live_pairs = [
        ('BTC', 'USD'),
        ('ETH', 'USD'),
        ('BNB', 'USD'),
    ]
    analyses: List[Dict[str, Any]] = []
    for base, quote in live_pairs:
        analysis = detector.analyze_symbol(base, quote)
        detector.print_anomaly_report(analysis)
        analyses.append(analysis)
        time.sleep(1)

    provider_analyses = [
        analysis for analysis in analyses
        if analysis.get('truth_status') == 'real_derived'
        and analysis.get('source_timestamp')
        and analysis.get('source_id')
    ]
    received_at = datetime.now(timezone.utc)
    return {
        'truth_status': 'real_derived' if provider_analyses else 'no_data',
        'source_id': (
            '|'.join(sorted({analysis['source_id'] for analysis in provider_analyses}))
            if provider_analyses else None
        ),
        'source_timestamp': (
            min(analysis['source_timestamp'] for analysis in provider_analyses)
            if provider_analyses else None
        ),
        'received_at': received_at.isoformat(),
        'generated_values': False,
        'eligible_for_external_action': False,
        'analyses': analyses,
        'anomalies_detected': len(detector.detected_anomalies),
        'refinements_recorded': len(detector.refinement_log),
    }


if __name__ == "__main__":
    run_live_anomaly_detection()
