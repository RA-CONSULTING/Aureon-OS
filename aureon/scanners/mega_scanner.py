#!/usr/bin/env python3
"""
🌍⚡🌍⚡🌍⚡🌍⚡🌍⚡🌍⚡🌍⚡🌍⚡🌍⚡🌍⚡🌍⚡🌍⚡🌍⚡🌍⚡🌍⚡🌍⚡🌍⚡🌍⚡🌍⚡🌍⚡
   MEGA SCANNER - SCAN THE ENTIRE CRYPTO MARKET!
🌍⚡🌍⚡🌍⚡🌍⚡🌍⚡🌍⚡🌍⚡🌍⚡🌍⚡🌍⚡🌍⚡🌍⚡🌍⚡🌍⚡🌍⚡🌍⚡🌍⚡🌍⚡🌍⚡🌍⚡

Scans ALL exchanges for:
├─ Price movements
├─ Volume spikes  
├─ Momentum waves
├─ Arbitrage opportunities
├─ Conversion paths
└─ Queen Sero's guidance

Gary Leckey & GitHub Copilot | January 2026
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import asyncio
import json
import hashlib
import math
import time
from collections.abc import Mapping
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

MAX_MARKET_DATA_AGE_SECONDS = 120.0
MAX_SOURCE_CLOCK_SKEW_SECONDS = 5.0


def _finite_number(value: Any, *, positive: bool = False) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or (positive and number <= 0):
        return None
    return number


def _required_number(
    payload: Mapping[str, Any],
    *keys: str,
    positive: bool = False,
) -> Optional[float]:
    for key in keys:
        if key in payload and payload[key] is not None:
            return _finite_number(payload[key], positive=positive)
    return None


def _required_text(payload: Mapping[str, Any], *keys: str) -> Optional[str]:
    for key in keys:
        if key in payload and payload[key] is not None:
            value = str(payload[key]).strip()
            if value:
                return value
    return None


def _parse_timestamp(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp /= 1000.0
        return timestamp if math.isfinite(timestamp) and timestamp > 0 else None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(raw)
        except (TypeError, ValueError, OverflowError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    timestamp = parsed.timestamp()
    return timestamp if math.isfinite(timestamp) and timestamp > 0 else None


def _no_data(exchange: str, reason: str) -> Dict[str, Any]:
    """Numeric-free denial receipt, ineligible for every downstream use."""
    return {
        "status": "no_data",
        "data_status": "no_data",
        "truth_status": "no_data",
        "exchange": exchange,
        "reason": reason,
        "source_id": None,
        "source_timestamp": None,
        "received_at": None,
        "receipt_id": None,
        "generated_values": False,
        "eligible_for_ranking": False,
        "eligible_for_action": False,
        "eligible_for_external_action": False,
        "eligible_for_accounting": False,
        "eligible_for_learning": False,
    }


def _content_receipt_id(
    source_id: str,
    symbol: str,
    source_timestamp: float,
    payload: Mapping[str, Any],
) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"{source_id}:{symbol}:{int(source_timestamp * 1_000_000)}:{digest}"


def _market_record(
    *,
    asset: str,
    pair: str,
    exchange: str,
    price: Any,
    volume: Any,
    change_24h: Any,
    source_id: Any,
    source_timestamp: Any,
    received_at: Any,
    receipt_id: Any,
    generated_values: Any,
    now: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    """Canonicalise a complete fresh provider record without numeric fallback."""
    asset_text = str(asset).strip()
    pair_text = str(pair).strip()
    exchange_text = str(exchange).strip().lower()
    price_value = _finite_number(price, positive=True)
    volume_value = _finite_number(volume)
    change_value = _finite_number(change_24h)
    observed_at = _parse_timestamp(source_timestamp)
    received = _parse_timestamp(received_at)
    source = str(source_id).strip() if source_id is not None else ""
    receipt = str(receipt_id).strip() if receipt_id is not None else ""
    current = time.time() if now is None else float(now)
    if (
        price_value is None
        or volume_value is None
        or volume_value < 0
        or change_value is None
        or observed_at is None
        or received is None
        or not asset_text
        or not pair_text
        or not exchange_text
        or not source
        or not receipt
        or generated_values is not False
        or not math.isfinite(current)
    ):
        return None
    source_age = current - observed_at
    receipt_age = current - received
    receipt_lag = received - observed_at
    if (
        source_age < -MAX_SOURCE_CLOCK_SKEW_SECONDS
        or source_age > MAX_MARKET_DATA_AGE_SECONDS
        or receipt_age < -MAX_SOURCE_CLOCK_SKEW_SECONDS
        or receipt_age > MAX_MARKET_DATA_AGE_SECONDS
        or receipt_lag < -MAX_SOURCE_CLOCK_SKEW_SECONDS
        or receipt_lag > MAX_MARKET_DATA_AGE_SECONDS
    ):
        return None
    return {
        "asset": asset_text,
        "pair": pair_text,
        "exchange": exchange_text,
        "price": price_value,
        "volume": volume_value,
        "change_24h": change_value,
        "source_id": source,
        "source_timestamp": observed_at,
        "received_at": received,
        "receipt_id": receipt,
        "data_status": "live",
        "truth_status": "real_derived",
        "generated_values": False,
        "eligible_for_ranking": True,
        "eligible_for_action": True,
        "eligible_for_external_action": True,
        "eligible_for_accounting": False,
        "eligible_for_learning": True,
    }

# ════════════════════════════════════════════════════════════════════════════════
# 📦 IMPORTS
# ════════════════════════════════════════════════════════════════════════════════

try:
    from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
    KRAKEN_OK = True
except ImportError:
    KrakenClient = None
    KRAKEN_OK = False

try:
    from aureon.exchanges.binance_client import BinanceClient, get_binance_client
    BINANCE_OK = True
except ImportError:
    BinanceClient = None
    BINANCE_OK = False

try:
    from aureon.exchanges.alpaca_client import AlpacaClient
    ALPACA_OK = True
except ImportError:
    AlpacaClient = None
    ALPACA_OK = False

try:
    from aureon.data_feeds.crypto_market_map import CryptoMarketMap, SYMBOL_TO_SECTOR, CRYPTO_SECTORS
    MARKET_MAP_OK = True
except ImportError:
    CryptoMarketMap = None
    MARKET_MAP_OK = False
    SYMBOL_TO_SECTOR = {}
    CRYPTO_SECTORS = {}


# ════════════════════════════════════════════════════════════════════════════════
# 🗺️ UNIVERSAL ASSET NORMALIZER
# ════════════════════════════════════════════════════════════════════════════════

KRAKEN_ASSET_MAP = {
    'XXBT': 'BTC', 'XBT': 'BTC',
    'XETH': 'ETH',
    'XXLM': 'XLM',
    'XLTC': 'LTC',
    'XXRP': 'XRP',
    'XXDG': 'DOGE', 'XDOGE': 'DOGE',
    'XZEC': 'ZEC',
    'XREP': 'REP',
    'XETC': 'ETC',
    'XMLN': 'MLN',
    'XXMR': 'XMR',
    'ZUSD': 'USD',
    'ZEUR': 'EUR',
    'ZGBP': 'GBP',
    'ZCAD': 'CAD',
    'ZJPY': 'JPY',
    'ZAUD': 'AUD',
}

STABLECOINS = {
    'USDT', 'USDC', 'TUSD', 'BUSD', 'DAI', 'USDP', 'GUSD', 'FRAX', 'LUSD',
    'PYUSD', 'USDD', 'FDUSD', 'MIM', 'SUSD', 'USD', 'EUR', 'GBP',
    'ZUSD', 'ZEUR', 'ZGBP', 'EURC', 'EURT',
}


def normalize_asset(asset: str, exchange: str = None) -> str:
    """Normalize asset name across all exchanges."""
    upper = asset.upper().strip()
    unstaked = upper.replace('.S', '')
    
    if exchange == 'kraken':
        if upper in KRAKEN_ASSET_MAP:
            return KRAKEN_ASSET_MAP[upper]
        if unstaked in KRAKEN_ASSET_MAP:
            return KRAKEN_ASSET_MAP[unstaked]
        if upper.startswith('XX') and len(upper) > 2:
            return upper[2:]
        if upper.startswith('X') and len(upper) > 1 and upper not in {'XRP', 'XLM', 'XTZ', 'XMR', 'XDC'}:
            return upper[1:]
        if upper.startswith('Z') and len(upper) > 1:
            return upper[1:]
    
    elif exchange == 'alpaca':
        if upper.endswith('/USD'):
            return upper[:-4]
        if upper.endswith('USD') and len(upper) > 3 and upper[:-3] not in STABLECOINS:
            return upper[:-3]
    
    return upper


# ════════════════════════════════════════════════════════════════════════════════
# 🌍⚡ MEGA SCANNER CLASS
# ════════════════════════════════════════════════════════════════════════════════

class MegaScanner:
    """
    Scans the ENTIRE crypto market across ALL exchanges!
    
    Features:
    ├─ Kraken: 1,400+ pairs
    ├─ Binance: 2,000+ pairs  
    ├─ Alpaca: 100+ pairs
    ├─ Momentum tracking
    ├─ Wave detection
    └─ Opportunity scoring
    """
    
    def __init__(self):
        print("🌍⚡" * 25)
        print("   MEGA SCANNER - SCAN EVERYTHING!")
        print("🌍⚡" * 25)
        print()
        
        # Exchange clients
        self.kraken = None
        self.binance = None
        self.alpaca = None
        
        # Market data
        self.prices: Dict[str, float] = {}
        self.volumes: Dict[str, float] = {}
        self.changes_24h: Dict[str, float] = {}
        self.momentum: Dict[str, float] = defaultdict(float)
        self.market_records: Dict[str, Dict[str, Any]] = {}
        self.no_data_by_exchange: Dict[str, Dict[str, Any]] = {}
        
        # Discovered assets
        self.all_assets: set = set()
        self.exchange_pairs = {
            'kraken': set(),
            'binance': set(),
            'alpaca': set(),
        }
        
        # Opportunities found
        self.opportunities: List[Dict] = []
        self.last_analysis_status: Dict[str, Any] = _no_data(
            "scanner",
            "not_scanned",
        )
        
        # Stats
        self.scan_count = 0
        self.last_scan = None

    def _clear_market_state(self) -> None:
        """Prevent previous-cycle provider values from being ranked as current."""
        self.prices.clear()
        self.volumes.clear()
        self.changes_24h.clear()
        self.momentum.clear()
        self.market_records.clear()
        self.no_data_by_exchange.clear()
        self.last_analysis_status = _no_data("scanner", "scan_in_progress")
        self.all_assets.clear()
        for pairs in self.exchange_pairs.values():
            pairs.clear()
        self.opportunities.clear()

    def _store_record(self, record: Dict[str, Any]) -> None:
        key = f"{record['exchange']}:{record['asset']}"
        self.market_records[key] = record
        self.prices[key] = record["price"]
        self.volumes[key] = record["volume"]
        self.changes_24h[key] = record["change_24h"]
        self.all_assets.add(record["asset"])
        self.exchange_pairs[record["exchange"]].add(record["pair"])

    def _record_no_data(self, exchange: str, reason: str) -> Dict[str, Any]:
        stale_keys = [
            key
            for key, record in self.market_records.items()
            if record.get("exchange") == exchange
        ]
        for key in stale_keys:
            self.market_records.pop(key, None)
            self.prices.pop(key, None)
            self.volumes.pop(key, None)
            self.changes_24h.pop(key, None)
        if exchange in self.exchange_pairs:
            self.exchange_pairs[exchange].clear()
        self.all_assets = {
            record["asset"]
            for record in self.market_records.values()
        }
        self.opportunities = [
            opportunity
            for opportunity in self.opportunities
            if opportunity.get("asset") not in stale_keys
        ]
        denial = _no_data(exchange, reason)
        self.no_data_by_exchange[exchange] = denial
        return denial

    @staticmethod
    def _record_is_fresh(record: Any, *, now: Optional[float] = None) -> bool:
        if not isinstance(record, Mapping):
            return False
        rebuilt = _market_record(
            asset=str(record.get("asset") or ""),
            pair=str(record.get("pair") or ""),
            exchange=str(record.get("exchange") or ""),
            price=record.get("price"),
            volume=record.get("volume"),
            change_24h=record.get("change_24h"),
            source_id=record.get("source_id"),
            source_timestamp=record.get("source_timestamp"),
            received_at=record.get("received_at"),
            receipt_id=record.get("receipt_id"),
            generated_values=record.get("generated_values"),
            now=now,
        )
        return (
            rebuilt is not None
            and record.get("data_status") == "live"
            and record.get("truth_status") in {"live", "real_observed", "real_derived"}
            and record.get("eligible_for_ranking") is True
            and record.get("eligible_for_action") is True
        )

    def _live_summary(self, exchange: str, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not records:
            return self._record_no_data(exchange, "no_complete_fresh_provider_records")
        latest = max(records, key=lambda item: item["source_timestamp"])
        self.no_data_by_exchange.pop(exchange, None)
        return {
            "status": "live",
            "data_status": "live",
            "truth_status": "real_derived",
            "exchange": exchange,
            "pairs": len(records),
            "source_id": latest["source_id"],
            "source_timestamp": latest["source_timestamp"],
            "received_at": latest["received_at"],
            "receipt_id": latest["receipt_id"],
            "generated_values": False,
            "eligible_for_ranking": True,
            "eligible_for_action": True,
            "eligible_for_external_action": True,
            "eligible_for_accounting": False,
            "eligible_for_learning": True,
        }

    def _ingest_kraken_payload(
        self,
        payload: Any,
        *,
        source_timestamp: Any,
        received_at: Any,
        receipt_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not isinstance(payload, Mapping):
            return self._record_no_data("kraken", "malformed_provider_payload")
        errors = payload.get("error")
        if errors:
            return self._record_no_data("kraken", "provider_reported_error")
        tickers = payload.get("result")
        observed_at = _parse_timestamp(source_timestamp)
        received = _parse_timestamp(received_at)
        if not isinstance(tickers, Mapping) or observed_at is None or received is None:
            return self._record_no_data("kraken", "missing_provider_receipt_evidence")
        batch_receipt = str(receipt_id or "").strip()
        if not batch_receipt:
            batch_receipt = _content_receipt_id(
                "kraken:/0/public/Ticker",
                "batch",
                observed_at,
                payload,
            )

        accepted: List[Dict[str, Any]] = []
        for pair, ticker_data in tickers.items():
            if str(pair).endswith(".d") or not isinstance(ticker_data, Mapping):
                continue
            if (
                "generated_values" in ticker_data
                and ticker_data["generated_values"] is not False
            ):
                continue
            closes = ticker_data.get("c")
            volumes = ticker_data.get("v")
            if (
                not isinstance(closes, list)
                or not closes
                or not isinstance(volumes, list)
                or len(volumes) < 2
            ):
                continue
            last_price = _finite_number(closes[0], positive=True)
            volume = _finite_number(volumes[1])
            open_price = _required_number(ticker_data, "o", positive=True)
            if last_price is None or volume is None or open_price is None:
                continue
            change = ((last_price - open_price) / open_price) * 100

            pair_text = str(pair)
            base = pair_text
            for quote in ['ZUSD', 'USD', 'USDT', 'USDC', 'ZEUR', 'EUR', 'ZGBP', 'GBP', 'XBT', 'ETH']:
                if pair_text.endswith(quote):
                    base = pair_text[:-len(quote)]
                    break
            base = normalize_asset(base, "kraken")
            if not base or len(base) > 10:
                continue
            record = _market_record(
                asset=base,
                pair=pair_text,
                exchange="kraken",
                price=last_price,
                volume=volume,
                change_24h=change,
                source_id="kraken:/0/public/Ticker",
                source_timestamp=observed_at,
                received_at=received,
                receipt_id=f"{batch_receipt}:{pair_text}",
                generated_values=False,
            )
            if record is not None:
                self._store_record(record)
                accepted.append(record)
        return self._live_summary("kraken", accepted)

    def _ingest_binance_payload(
        self,
        payload: Any,
        *,
        received_at: Any,
    ) -> Dict[str, Any]:
        received = _parse_timestamp(received_at)
        if not isinstance(payload, list) or received is None:
            return self._record_no_data("binance", "malformed_provider_payload")
        accepted: List[Dict[str, Any]] = []
        for ticker in payload:
            if not isinstance(ticker, Mapping):
                continue
            if "generated_values" in ticker and ticker["generated_values"] is not False:
                continue
            symbol = _required_text(ticker, "symbol")
            observed_at = _parse_timestamp(
                ticker["source_timestamp"]
                if "source_timestamp" in ticker
                else ticker["closeTime"]
                if "closeTime" in ticker
                else ticker["eventTime"]
                if "eventTime" in ticker
                else None
            )
            last_price = _required_number(ticker, "lastPrice", positive=True)
            volume = _required_number(ticker, "quoteVolume")
            change = _required_number(ticker, "priceChangePercent")
            if None in (symbol, observed_at, last_price, volume, change):
                continue
            assert symbol is not None and observed_at is not None
            assert last_price is not None and volume is not None and change is not None

            base = symbol
            for quote in ['USDT', 'USDC', 'BUSD', 'FDUSD', 'USD', 'EUR', 'GBP', 'BTC', 'ETH', 'BNB', 'TRY', 'TUSD']:
                if symbol.endswith(quote):
                    base = symbol[:-len(quote)]
                    break
            if not base or base in STABLECOINS or len(base) > 10:
                continue
            source_id = _required_text(ticker, "source_id") or "binance:/api/v3/ticker/24hr"
            ticker_receipt = _required_text(ticker, "receipt_id") or _content_receipt_id(
                source_id,
                symbol,
                observed_at,
                ticker,
            )
            record = _market_record(
                asset=base,
                pair=symbol,
                exchange="binance",
                price=last_price,
                volume=volume,
                change_24h=change,
                source_id=source_id,
                source_timestamp=observed_at,
                received_at=received,
                receipt_id=ticker_receipt,
                generated_values=False,
            )
            if record is not None:
                self._store_record(record)
                accepted.append(record)
        return self._live_summary("binance", accepted)

    def _ingest_alpaca_positions(self, positions: Any) -> Dict[str, Any]:
        if not isinstance(positions, list):
            return self._record_no_data("alpaca", "malformed_provider_payload")
        accepted: List[Dict[str, Any]] = []
        for position in positions:
            if not isinstance(position, Mapping):
                continue
            symbol = _required_text(position, "symbol")
            current_price = _required_number(position, "current_price", positive=True)
            volume = _required_number(position, "quoteVolume", "quote_volume", "volume")
            change = _required_number(
                position,
                "priceChangePercent",
                "change_24h",
                "change24h",
            )
            if None in (symbol, current_price, volume, change):
                continue
            assert symbol is not None and current_price is not None
            assert volume is not None and change is not None
            base = normalize_asset(symbol, "alpaca")
            record = _market_record(
                asset=base,
                pair=symbol,
                exchange="alpaca",
                price=current_price,
                volume=volume,
                change_24h=change,
                source_id=_required_text(position, "source_id"),
                source_timestamp=position.get("source_timestamp"),
                received_at=position.get("received_at"),
                receipt_id=_required_text(position, "receipt_id"),
                generated_values=position.get("generated_values"),
            )
            if record is not None:
                self._store_record(record)
                accepted.append(record)
        return self._live_summary("alpaca", accepted)
        
    async def connect_exchanges(self):
        """Connect to all exchanges."""
        print("📡 Connecting to exchanges...")
        
        if KRAKEN_OK:
            try:
                self.kraken = get_kraken_client()
                print("   🐙 Kraken: CONNECTED")
            except Exception as e:
                print(f"   🐙 Kraken: FAILED - {e}")
        
        if BINANCE_OK:
            try:
                self.binance = get_binance_client()
                print("   🟡 Binance: CONNECTED")
            except Exception as e:
                print(f"   🟡 Binance: FAILED - {e}")
        
        if ALPACA_OK:
            try:
                self.alpaca = AlpacaClient()
                print("   🦙 Alpaca: CONNECTED")
            except Exception as e:
                print(f"   🦙 Alpaca: FAILED - {e}")
        
        print()
    
    async def fetch_kraken_data(self) -> Dict[str, Any]:
        """Fetch all market data from Kraken."""
        if not self.kraken:
            return self._record_no_data("kraken", "provider_client_unavailable")
        
        try:
            print("   🐙 Fetching Kraken tickers...")
            
            # Use the Ticker API directly
            import requests
            resp = requests.get("https://api.kraken.com/0/public/Ticker", timeout=30)
            received_at = time.time()
            resp.raise_for_status()
            data = resp.json()
            headers = resp.headers if isinstance(resp.headers, Mapping) else {}
            provider_timestamp = _parse_timestamp(headers.get("Date"))
            response_receipt = _required_text(headers, "X-Request-ID", "CF-Ray")
            result = self._ingest_kraken_payload(
                data,
                source_timestamp=provider_timestamp,
                received_at=received_at,
                receipt_id=response_receipt,
            )
            if result["status"] == "live":
                print(f"   🐙 Kraken: {result['pairs']} pairs loaded")
            else:
                print(f"   🐙 Kraken: NO_DATA - {result['reason']}")
            return result
            
        except Exception as e:
            print(f"   🐙 Kraken error: {e}")
            return self._record_no_data("kraken", "provider_request_failed")
    
    async def fetch_binance_data(self) -> Dict[str, Any]:
        """Fetch all market data from Binance."""
        try:
            print("   🟡 Fetching Binance tickers...")
            
            # Use Binance API directly
            import requests
            resp = requests.get("https://api.binance.com/api/v3/ticker/24hr", timeout=30)
            received_at = time.time()
            resp.raise_for_status()
            tickers = resp.json()
            result = self._ingest_binance_payload(
                tickers,
                received_at=received_at,
            )
            if result["status"] == "live":
                print(f"   🟡 Binance: {result['pairs']} pairs loaded")
            else:
                print(f"   🟡 Binance: NO_DATA - {result['reason']}")
            return result
            
        except Exception as e:
            print(f"   🟡 Binance error: {e}")
            return self._record_no_data("binance", "provider_request_failed")
    
    async def fetch_alpaca_data(self) -> Dict[str, Any]:
        """Fetch all market data from Alpaca."""
        if not self.alpaca:
            return self._record_no_data("alpaca", "provider_client_unavailable")
        
        try:
            print("   🦙 Fetching Alpaca tickers...")
            
            # Get positions and latest quotes
            positions = self.alpaca.get_positions() if hasattr(self.alpaca, 'get_positions') else []
            result = self._ingest_alpaca_positions(positions)
            if result["status"] == "live":
                print(f"   🦙 Alpaca: {result['pairs']} positions loaded")
            else:
                print(f"   🦙 Alpaca: NO_DATA - {result['reason']}")
            return result
            
        except Exception as e:
            print(f"   🦙 Alpaca error: {e}")
            return self._record_no_data("alpaca", "provider_request_failed")
    
    async def scan(self):
        """Run a full market scan."""
        print()
        print("📊 Fetching ALL market data...")
        print()

        # A scan cycle may rank only receipts obtained in this cycle.
        self._clear_market_state()
        
        # Fetch from all exchanges concurrently
        results = await asyncio.gather(
            self.fetch_kraken_data(),
            self.fetch_binance_data(),
            self.fetch_alpaca_data(),
            return_exceptions=True
        )
        
        # Handle any exceptions
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"   ⚠️ Exchange {i} error: {result}")
        
        self.scan_count += 1
        self.last_scan = datetime.now()
        
        # Analyze opportunities
        await self.analyze_opportunities()
        
        # Print summary
        self.print_summary()
    
    async def analyze_opportunities(self):
        """Analyze market for opportunities."""
        self.opportunities = []
        now = time.time()
        eligible_records = {
            key: record
            for key, record in self.market_records.items()
            if self._record_is_fresh(record, now=now)
        }
        if not eligible_records:
            self.last_analysis_status = _no_data(
                "scanner",
                "no_complete_fresh_provider_records",
            )
            return self.last_analysis_status
        
        # Find top movers
        top_gainers = sorted(
            [
                (key, record["change_24h"])
                for key, record in eligible_records.items()
                if record["change_24h"] > 0
            ],
            key=lambda x: x[1],
            reverse=True
        )[:20]
        
        top_losers = sorted(
            [
                (key, record["change_24h"])
                for key, record in eligible_records.items()
                if record["change_24h"] < 0
            ],
            key=lambda x: x[1]
        )[:20]
        
        # Find volume spikes (simplified)
        high_volume = sorted(
            [
                (key, record["volume"])
                for key, record in eligible_records.items()
                if record["volume"] > 1000000
            ],
            key=lambda x: x[1],
            reverse=True
        )[:20]
        
        # Store opportunities
        for asset, change in top_gainers[:10]:
            record = eligible_records[asset]
            self.opportunities.append({
                'type': 'TOP_GAINER',
                'asset': asset,
                'change_24h': change,
                'price': record["price"],
                'volume': record["volume"],
                'source_id': record["source_id"],
                'source_timestamp': record["source_timestamp"],
                'received_at': record["received_at"],
                'receipt_id': record["receipt_id"],
                'data_status': "live",
                'truth_status': "real_derived",
                'generated_values': False,
                'eligible_for_ranking': True,
                'eligible_for_action': True,
                'eligible_for_external_action': True,
                'eligible_for_accounting': False,
                'eligible_for_learning': True,
            })
        
        for asset, change in top_losers[:10]:
            record = eligible_records[asset]
            self.opportunities.append({
                'type': 'TOP_LOSER',
                'asset': asset,
                'change_24h': change,
                'price': record["price"],
                'volume': record["volume"],
                'source_id': record["source_id"],
                'source_timestamp': record["source_timestamp"],
                'received_at': record["received_at"],
                'receipt_id': record["receipt_id"],
                'data_status': "live",
                'truth_status': "real_derived",
                'generated_values': False,
                'eligible_for_ranking': True,
                'eligible_for_action': True,
                'eligible_for_external_action': True,
                'eligible_for_accounting': False,
                'eligible_for_learning': True,
            })
        latest = max(
            eligible_records.values(),
            key=lambda record: record["source_timestamp"],
        )
        self.last_analysis_status = {
            "status": "live",
            "data_status": "live",
            "truth_status": "real_derived",
            "records_ranked": len(eligible_records),
            "opportunities_found": len(self.opportunities),
            "source_id": latest["source_id"],
            "source_timestamp": latest["source_timestamp"],
            "received_at": latest["received_at"],
            "receipt_id": latest["receipt_id"],
            "generated_values": False,
            "eligible_for_ranking": True,
            "eligible_for_action": True,
            "eligible_for_external_action": True,
            "eligible_for_accounting": False,
            "eligible_for_learning": True,
        }
        return self.last_analysis_status
    
    def print_summary(self):
        """Print scan summary."""
        print()
        print("═" * 70)
        print("🌍⚡ MEGA SCANNER RESULTS 🌍⚡")
        print("═" * 70)
        print()
        
        # Exchange stats
        print("📊 EXCHANGE COVERAGE:")
        print(f"   🐙 Kraken:  {len(self.exchange_pairs['kraken']):,} pairs")
        print(f"   🟡 Binance: {len(self.exchange_pairs['binance']):,} pairs")
        print(f"   🦙 Alpaca:  {len(self.exchange_pairs['alpaca']):,} pairs")
        print(f"   📈 TOTAL:   {sum(len(p) for p in self.exchange_pairs.values()):,} pairs")
        print(f"   🪙 Unique Assets: {len(self.all_assets):,}")
        print()
        
        # Top gainers
        gainers = [o for o in self.opportunities if o['type'] == 'TOP_GAINER']
        if gainers:
            print("🚀 TOP GAINERS (24h):")
            for i, opp in enumerate(gainers[:10], 1):
                print(f"   {i:2}. {opp['asset']:20} +{opp['change_24h']:.2f}%  (${opp['price']:.4f})")
            print()
        
        # Top losers
        losers = [o for o in self.opportunities if o['type'] == 'TOP_LOSER']
        if losers:
            print("📉 TOP LOSERS (24h):")
            for i, opp in enumerate(losers[:10], 1):
                print(f"   {i:2}. {opp['asset']:20} {opp['change_24h']:.2f}%  (${opp['price']:.4f})")
            print()
        
        # Sector breakdown
        if SYMBOL_TO_SECTOR:
            print("🏷️ SECTOR BREAKDOWN:")
            sector_counts = defaultdict(int)
            for asset in self.all_assets:
                sector = SYMBOL_TO_SECTOR.get(asset, 'unknown')
                sector_counts[sector] += 1
            
            for sector, count in sorted(sector_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"   {sector:15} {count:4} assets")
            print()
        
        print(f"⏱️ Scan #{self.scan_count} completed at {self.last_scan}")
        print("═" * 70)
    
    async def run_continuous(self, interval_seconds: int = 30, max_scans: int = None):
        """Run continuous scanning."""
        await self.connect_exchanges()
        
        scans = 0
        while max_scans is None or scans < max_scans:
            await self.scan()
            scans += 1
            
            if max_scans and scans >= max_scans:
                break
            
            print(f"\n⏳ Next scan in {interval_seconds} seconds... (Ctrl+C to stop)\n")
            await asyncio.sleep(interval_seconds)


# ════════════════════════════════════════════════════════════════════════════════
# 🚀 MAIN
# ════════════════════════════════════════════════════════════════════════════════

async def main():
    """Run the mega scanner."""
    scanner = MegaScanner()
    
    # Run 3 scans with 10 second intervals
    await scanner.run_continuous(interval_seconds=10, max_scans=3)


if __name__ == "__main__":
    print()
    asyncio.run(main())
