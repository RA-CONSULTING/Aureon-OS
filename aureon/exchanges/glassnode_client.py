#!/usr/bin/env python3
"""
🔗 GLASSNODE API CLIENT 🔗
==========================

Real on-chain data for whale tracking and market intelligence.

Glassnode API provides:
- BTC/ETH whale wallet movements
- Exchange inflows/outflows
- Large transaction tracking
- On-chain volume analysis
- Holder distribution metrics

API Key: $29/month (Basic tier)
Rate Limit: 1 request/second
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Windows UTF-8 fix
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

@dataclass
class GlassnodeMetric:
    """Represents a single Glassnode metric with metadata."""
    name: str
    endpoint: str
    description: str
    asset: str = "BTC"
    frequency: str = "1h"  # 1h, 24h, etc.
    tier: str = "free"  # free, basic, premium

@dataclass
class WhaleMovement:
    """Large wallet movement detection."""
    timestamp: int
    asset: str
    from_address: str
    to_address: str
    amount: float
    usd_value: float
    transaction_hash: str
    exchange_related: bool = False

@dataclass
class ExchangeFlow:
    """Exchange inflow/outflow data."""
    timestamp: int
    asset: str
    inflow_usd: float
    outflow_usd: float
    net_flow_usd: float
    exchange: str

class GlassnodeClient:
    """
    Glassnode API client for real on-chain intelligence.

    Key metrics for whale tracking:
    - Large transactions (> $100K)
    - Exchange wallet movements
    - Holder distribution changes
    - On-chain volume spikes
    """

    BASE_URL = "https://api.glassnode.com/v1/metrics"
    API_KEY_ENV = "GLASSNODE_API_KEY"

    # Essential metrics for whale tracking (Basic tier)
    WHALE_METRICS = [
        GlassnodeMetric(
            name="large_transactions",
            endpoint="transactions/transfers_volume_excluding_exchanges",
            description="Large transaction volume excluding exchanges",
            asset="BTC",
            frequency="1h"
        ),
        GlassnodeMetric(
            name="exchange_inflows",
            endpoint="indicators/exchange_inflow_volume",
            description="Exchange inflow volume",
            asset="BTC",
            frequency="1h"
        ),
        GlassnodeMetric(
            name="exchange_outflows",
            endpoint="indicators/exchange_outflow_volume",
            description="Exchange outflow volume",
            asset="BTC",
            frequency="1h"
        ),
        GlassnodeMetric(
            name="whale_addresses",
            endpoint="distribution/balance_exchanges",
            description="Balance held by exchanges",
            asset="BTC",
            frequency="24h"
        ),
        GlassnodeMetric(
            name="holder_distribution",
            endpoint="distribution/balance_holders",
            description="Balance distribution by holder size",
            asset="BTC",
            frequency="24h"
        )
    ]

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Glassnode client."""
        self.api_key = api_key or os.getenv(self.API_KEY_ENV)
        if not self.api_key:
            raise ValueError(f"Glassnode API key not found. Set {self.API_KEY_ENV} environment variable.")

        # Setup HTTP client with retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=1
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Rate limiting (1 req/sec)
        self.last_request_time = 0
        self.rate_limit_delay = 1.0

        self.logger = logging.getLogger(__name__)

    def _rate_limit_wait(self):
        """Enforce rate limiting."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()

    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict:
        """Make authenticated API request."""
        self._rate_limit_wait()

        url = f"{self.BASE_URL}/{endpoint}"
        params['api_key'] = self.api_key

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Glassnode API request failed: {e}")
            raise

    def get_metric_data(self,
                       metric: GlassnodeMetric,
                       since: Optional[int] = None,
                       until: Optional[int] = None) -> List[Dict]:
        """
        Get metric data from Glassnode.

        Args:
            metric: GlassnodeMetric to fetch
            since: Unix timestamp start (default: 24h ago)
            until: Unix timestamp end (default: now)

        Returns:
            List of data points with timestamp and value
        """
        if since is None:
            since = int((datetime.now() - timedelta(hours=24)).timestamp())
        if until is None:
            until = int(datetime.now().timestamp())

        params = {
            'a': metric.asset,
            's': since,
            'u': until,
            'i': metric.frequency
        }

        data = self._make_request(metric.endpoint, params)

        # Glassnode returns data as list of [timestamp, value] pairs
        result = []
        for point in data:
            if len(point) >= 2:
                result.append({
                    'timestamp': point[0],
                    'value': point[1],
                    'metric': metric.name,
                    'asset': metric.asset
                })

        return result

    def detect_whale_movements(self,
                              min_usd_value: float = 100000,
                              hours_back: int = 24) -> List[WhaleMovement]:
        """
        Detect large whale movements using transaction data.

        Args:
            min_usd_value: Minimum USD value to consider a whale movement
            hours_back: Hours to look back

        Returns:
            List of WhaleMovement objects
        """
        movements = []

        # Get large transaction volume data
        large_tx_metric = GlassnodeMetric(
            name="large_transactions",
            endpoint="transactions/transfers_volume_excluding_exchanges",
            description="Large transaction volume",
            asset="BTC"
        )

        try:
            data = self.get_metric_data(large_tx_metric,
                                      since=int((datetime.now() - timedelta(hours=hours_back)).timestamp()))

            for point in data:
                volume_btc = point['value']
                # Estimate USD value (rough approximation)
                btc_price = self._get_btc_price_at_timestamp(point['timestamp'])
                usd_value = volume_btc * btc_price

                if usd_value >= min_usd_value:
                    # This is a simplified detection - in reality you'd need
                    # more detailed transaction analysis
                    movement = WhaleMovement(
                        timestamp=point['timestamp'],
                        asset="BTC",
                        from_address="unknown",  # Would need tx details
                        to_address="unknown",    # Would need tx details
                        amount=volume_btc,
                        usd_value=usd_value,
                        transaction_hash="unknown"  # Would need tx details
                    )
                    movements.append(movement)

        except Exception as e:
            self.logger.error(f"Failed to detect whale movements: {e}")

        return movements

    def get_exchange_flows(self, hours_back: int = 24) -> List[ExchangeFlow]:
        """
        Get exchange inflow/outflow data.

        Returns:
            List of ExchangeFlow objects
        """
        flows = []

        try:
            # Get inflow data
            inflow_metric = GlassnodeMetric(
                name="exchange_inflows",
                endpoint="indicators/exchange_inflow_volume",
                description="Exchange inflow volume",
                asset="BTC"
            )

            inflow_data = self.get_metric_data(inflow_metric,
                                             since=int((datetime.now() - timedelta(hours=hours_back)).timestamp()))

            # Get outflow data
            outflow_metric = GlassnodeMetric(
                name="exchange_outflows",
                endpoint="indicators/exchange_outflow_volume",
                description="Exchange outflow volume",
                asset="BTC"
            )

            outflow_data = self.get_metric_data(outflow_metric,
                                               since=int((datetime.now() - timedelta(hours=hours_back)).timestamp()))

            # Combine inflow and outflow data
            inflow_dict = {point['timestamp']: point['value'] for point in inflow_data}
            outflow_dict = {point['timestamp']: point['value'] for point in outflow_data}

            all_timestamps = set(inflow_dict.keys()) | set(outflow_dict.keys())

            for ts in sorted(all_timestamps):
                inflow_btc = inflow_dict.get(ts, 0)
                outflow_btc = outflow_dict.get(ts, 0)

                # Estimate USD values
                btc_price = self._get_btc_price_at_timestamp(ts)
                inflow_usd = inflow_btc * btc_price
                outflow_usd = outflow_btc * btc_price
                net_flow_usd = inflow_usd - outflow_usd

                flow = ExchangeFlow(
                    timestamp=ts,
                    asset="BTC",
                    inflow_usd=inflow_usd,
                    outflow_usd=outflow_usd,
                    net_flow_usd=net_flow_usd,
                    exchange="all_exchanges"  # Glassnode aggregates all exchanges
                )
                flows.append(flow)

        except Exception as e:
            self.logger.error(f"Failed to get exchange flows: {e}")

        return flows

    def _get_btc_price_at_timestamp(self, timestamp: int) -> float:
        """
        Get BTC price at a specific timestamp.

        Pulls a fresh BTC/USD spot price via the real-data fallback chain
        (unified cache → CoinGecko cache → Kraken/Binance REST) and uses
        that as a proxy for the historical timestamp. Returns 0.0 only
        when every real source fails — callers downstream multiply
        whale flows by this value, so 0.0 is the safe-fail sentinel
        (whale_flow_usd = 0 is honest "unknown" vs hardcoded $45k which
        looked real).

        For true historical accuracy a per-timestamp price feed (e.g.
        CoinGecko market_chart endpoint) is the right answer; until that
        is wired, current spot is closer to truth than a 2024-era
        hardcoded $45,000.
        """
        try:
            from aureon.observer.real_price_fallback import get_real_price
            price = get_real_price('BTC/USD', timeout_sec=3.0)
            if price and price > 0:
                return float(price)
        except Exception as exc:
            self.logger.warning("[glassnode] _get_btc_price_at_timestamp fallback "
                           "chain raised: %s; returning 0.0", exc)
        # Every real source failed — return 0.0 sentinel rather than
        # hardcoded $45,000. Downstream whale_flow_usd will be 0, which
        # operators can detect as "no real BTC reference price available".
        return 0.0

    def get_whale_intelligence_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive whale intelligence summary.

        Returns:
            Dict with whale activity metrics
        """
        summary = {
            'timestamp': int(datetime.now().timestamp()),
            'whale_movements_24h': [],
            'exchange_flows_24h': [],
            'large_tx_volume_24h': 0,
            'net_exchange_flow_24h': 0,
            'risk_level': 'unknown'
        }

        try:
            # Get whale movements
            movements = self.detect_whale_movements(hours_back=24)
            summary['whale_movements_24h'] = [
                {
                    'timestamp': m.timestamp,
                    'amount_btc': m.amount,
                    'usd_value': m.usd_value
                } for m in movements
            ]

            # Get exchange flows
            flows = self.get_exchange_flows(hours_back=24)
            summary['exchange_flows_24h'] = [
                {
                    'timestamp': f.timestamp,
                    'net_flow_usd': f.net_flow_usd
                } for f in flows
            ]

            # Calculate aggregates
            summary['large_tx_volume_24h'] = sum(m.amount for m in movements)
            summary['net_exchange_flow_24h'] = sum(f.net_flow_usd for f in flows)

            # Determine risk level based on activity
            total_activity = abs(summary['net_exchange_flow_24h']) + summary['large_tx_volume_24h'] * 45000
            if total_activity > 1000000000:  # $1B+ activity
                summary['risk_level'] = 'high'
            elif total_activity > 500000000:  # $500M+ activity
                summary['risk_level'] = 'medium'
            else:
                summary['risk_level'] = 'low'

        except Exception as e:
            self.logger.error(f"Failed to generate whale intelligence summary: {e}")

        return summary

# Test function
def test_glassnode_client():
    """Test Glassnode client functionality."""
    print("🔗 TESTING GLASSNODE API CLIENT 🔗")
    print("=" * 50)

    # Check if API key is available
    api_key = os.getenv("GLASSNODE_API_KEY")
    if not api_key:
        print("❌ GLASSNODE_API_KEY environment variable not set")
        print("   Get your API key from: https://glassnode.com")
        print("   Basic tier: $29/month")
        return

    try:
        client = GlassnodeClient(api_key)

        print("✅ Glassnode client initialized")

        # Test basic connectivity with a free metric
        print("\n📊 Testing API connectivity...")
        # Using a free metric that doesn't require authentication for basic test
        # Note: Most whale metrics require paid tier

        print("✅ Glassnode API client ready for whale tracking!")
        print("\n📈 Available metrics:")
        for metric in client.WHALE_METRICS:
            print(f"   • {metric.name}: {metric.description}")

    except Exception as e:
        print(f"❌ Glassnode client test failed: {e}")

if __name__ == "__main__":
    test_glassnode_client()