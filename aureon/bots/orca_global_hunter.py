#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🦈🌍 ORCA GLOBAL HUNTER - THE WORLD NEVER SLEEPS 🌍🦈
═══════════════════════════════════════════════════════════════════════════════

"Why look at a puddle when you can hunt the entire ocean?"

The markets NEVER sleep:
  🌏 ASIA (Tokyo, Hong Kong, Singapore) - Active 00:00-09:00 UTC
  🌍 EUROPE (London, Frankfurt) - Active 07:00-16:00 UTC  
  🌎 AMERICAS (NYSE, NASDAQ) - Active 14:30-21:00 UTC
  🪙 CRYPTO - 24/7/365 ALWAYS

EXCHANGE COVERAGE:
  🐙 KRAKEN: 1,419 crypto pairs (24/7)
  🦙 ALPACA: 62 crypto + 10,000 stocks (crypto 24/7, stocks market hours)
  🟡 BINANCE: 1,565 pairs (24/7 - data only for UK)

TOTAL HUNTING GROUNDS: ~13,000+ opportunities!

Gary Leckey | Orca Never Sleeps | January 2026
═══════════════════════════════════════════════════════════════════════════════
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
import os

# Windows UTF-8 Fix
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        def _is_utf8_wrapper(stream):
            return (isinstance(stream, io.TextIOWrapper) and 
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        if hasattr(sys.stdout, 'buffer') and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

import time
import asyncio
import logging
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple, Any
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# 🌍 MARKET SESSION TRACKING
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MarketSession:
    """A global market session with its active hours."""
    name: str
    region: str
    utc_open: int  # Hour UTC
    utc_close: int  # Hour UTC
    exchanges: List[str]
    asset_types: List[str]  # 'crypto', 'stock', 'forex', 'commodity'
    
    def is_active(self) -> bool:
        """Check if this session is currently active."""
        now = datetime.now(timezone.utc)
        hour = now.hour
        
        # Handle overnight sessions (e.g., 22:00-06:00)
        if self.utc_open > self.utc_close:
            return hour >= self.utc_open or hour < self.utc_close
        else:
            return self.utc_open <= hour < self.utc_close

# Global market sessions
MARKET_SESSIONS = [
    # CRYPTO - Always active!
    MarketSession("Crypto Global", "GLOBAL", 0, 24, ["kraken", "alpaca", "binance"], ["crypto"]),
    
    # Asia Pacific
    MarketSession("Tokyo", "ASIA", 0, 6, ["binance"], ["crypto"]),
    MarketSession("Hong Kong", "ASIA", 1, 8, ["binance"], ["crypto"]),
    MarketSession("Singapore", "ASIA", 1, 9, ["binance"], ["crypto"]),
    
    # Europe
    MarketSession("London", "EUROPE", 8, 16, ["kraken", "binance"], ["crypto"]),
    MarketSession("Frankfurt", "EUROPE", 7, 15, ["kraken", "binance"], ["crypto"]),
    
    # Americas
    MarketSession("New York Pre", "AMERICAS", 13, 14, ["alpaca"], ["stock"]),  # Pre-market
    MarketSession("New York Main", "AMERICAS", 14, 21, ["alpaca"], ["stock", "crypto"]),  # Main
    MarketSession("New York After", "AMERICAS", 21, 24, ["alpaca"], ["stock"]),  # After-hours
]


@dataclass
class GlobalOpportunity:
    """A hunting opportunity from any global market."""
    symbol: str
    exchange: str
    region: str
    
    # Direction and strength
    direction: str  # 'buy' or 'sell'
    momentum_pct: float  # % move that triggered signal
    confidence: float  # 0-1
    
    # Prices
    current_price: float
    entry_price: float
    
    # Costs and profitability
    fee_pct: float
    spread_pct: float
    net_edge: float  # Expected profit after costs
    
    # Metadata
    source: str  # Which scanner found it
    reason: str
    volume: float

    # Every external-action candidate carries the provider event time separately
    # from Aureon's local receipt time. Derived values retain their input lineage.
    truth_status: str
    source_id: str
    source_timestamp: float
    received_at: float
    generated_values: bool
    eligible_for_external_action: bool
    field_provenance: Dict[str, Any]

    @property
    def timestamp(self) -> float:
        """Compatibility alias: signal time is the provider event time."""
        return self.source_timestamp
    
    @property
    def is_profitable(self) -> bool:
        """Only complete, provider-backed opportunities may be actionable."""
        numeric_values = (
            self.momentum_pct,
            self.confidence,
            self.current_price,
            self.entry_price,
            self.fee_pct,
            self.spread_pct,
            self.net_edge,
            self.volume,
            self.source_timestamp,
            self.received_at,
        )
        return (
            self.truth_status in {"live", "real_derived"}
            and bool(self.source_id)
            and self.generated_values is False
            and self.eligible_for_external_action is True
            and all(math.isfinite(value) for value in numeric_values)
            and self.current_price > 0
            and self.entry_price > 0
            and self.fee_pct > 0
            and self.spread_pct >= 0
            and self.volume > 0
            and self.net_edge > 0
            and bool(self.field_provenance)
            and self._is_fresh()
        )

    def _is_fresh(self) -> bool:
        now = time.time()
        return (
            now - self.source_timestamp <= 2 * 60 * 60
            and self.source_timestamp - now <= 5 * 60
            and now - self.received_at <= 2 * 60 * 60
            and self.received_at - self.source_timestamp <= 2 * 60 * 60
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 🦈 ORCA GLOBAL HUNTER
# ═══════════════════════════════════════════════════════════════════════════════

class OrcaGlobalHunter:
    """
    🦈 THE ORCA GLOBAL HUNTER - Scans ALL markets, ALL exchanges, 24/7
    
    The Orca never sleeps because the world never sleeps.
    When one market closes, another opens.
    There's ALWAYS prey somewhere.
    """
    
    def __init__(self):
        self.exchanges: Dict[str, Any] = {}
        self.universes: Dict[str, Set[str]] = {}
        self.opportunities: List[GlobalOpportunity] = []
        
        # Momentum thresholds (must beat costs!)
        self.min_momentum_pct = 0.5  # 0.5% minimum move
        
        # Stats
        self.total_scanned = 0
        self.scan_count = 0
        
        self._init_exchanges()

    @staticmethod
    def _number(value: Any, *, positive: bool = False) -> Optional[float]:
        """Return a finite provider number without inventing a fallback value."""
        if value is None or isinstance(value, bool):
            return None
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if not math.isfinite(number):
            return None
        if positive and number <= 0:
            return None
        return number

    @classmethod
    def _source_time(cls, value: Any) -> Optional[float]:
        """Normalize a provider timestamp; local receipt time is never a substitute."""
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return None
            numeric = cls._number(text)
            if numeric is None:
                try:
                    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=timezone.utc)
                    numeric = parsed.timestamp()
                except (TypeError, ValueError, OverflowError):
                    return None
        else:
            numeric = cls._number(value)
        if numeric is None or numeric <= 0:
            return None
        while numeric > 100_000_000_000:
            numeric /= 1000.0
        return numeric if math.isfinite(numeric) and numeric > 0 else None

    @staticmethod
    def _fresh(source_timestamp: float, received_at: float, max_age_seconds: float) -> bool:
        return (
            math.isfinite(source_timestamp)
            and math.isfinite(received_at)
            and source_timestamp > 0
            and received_at - source_timestamp <= max_age_seconds
            and source_timestamp - received_at <= 5 * 60
        )

    @classmethod
    def _quote_metrics(cls, bid_value: Any, ask_value: Any) -> Optional[Dict[str, float]]:
        bid = cls._number(bid_value, positive=True)
        ask = cls._number(ask_value, positive=True)
        if bid is None or ask is None or ask < bid:
            return None
        mid = (bid + ask) / 2.0
        if not math.isfinite(mid) or mid <= 0:
            return None
        return {
            "bid": bid,
            "ask": ask,
            "mid": mid,
            "spread_decimal": (ask - bid) / mid,
        }

    @classmethod
    def _kraken_server_time(cls, client: Any) -> Optional[float]:
        try:
            payload = client._public_get("/0/public/Time")
        except Exception as exc:
            logger.debug("Kraken provider time unavailable: %s", exc)
            return None
        if not isinstance(payload, dict):
            return None
        return cls._source_time(payload.get("unixtime"))

    @staticmethod
    def _kraken_pair_info(client: Any, symbol: str, pairs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        compact = str(symbol).replace("/", "").upper()
        for internal, raw in pairs.items():
            if not isinstance(raw, dict):
                continue
            aliases = {
                str(internal).replace("/", "").upper(),
                str(raw.get("altname") or "").replace("/", "").upper(),
                str(raw.get("wsname") or "").replace("/", "").upper(),
            }
            if compact in aliases:
                return raw
        return None

    @staticmethod
    def _canonical_crypto_base(base: str) -> str:
        aliases = {"XBT": "BTC", "XDG": "DOGE"}
        normalized = str(base).upper()
        return aliases.get(normalized, normalized)

    @classmethod
    def _kraken_canonical_compact(cls, pair_info: Dict[str, Any]) -> Optional[str]:
        wsname = pair_info.get("wsname") if isinstance(pair_info, dict) else None
        if isinstance(wsname, str) and "/" in wsname:
            base, quote = wsname.split("/", 1)
        else:
            altname = pair_info.get("altname") if isinstance(pair_info, dict) else None
            if not isinstance(altname, str):
                return None
            compact = altname.replace("/", "").upper()
            quote = next((suffix for suffix in ("USD", "USDC", "USDT") if compact.endswith(suffix)), "")
            if not quote:
                return None
            base = compact[:-len(quote)]
        canonical_quote = str(quote).upper()
        if canonical_quote != "USD":
            return None
        canonical_base = cls._canonical_crypto_base(base)
        return f"{canonical_base}USD" if canonical_base else None

    @classmethod
    def _kraken_fee_rate(cls, pair_info: Dict[str, Any]) -> Optional[float]:
        """Use Kraken's provider-returned zero-volume taker tier conservatively."""
        schedule = pair_info.get("fees") if isinstance(pair_info, dict) else None
        if not isinstance(schedule, list):
            return None
        zero_volume_rates: List[float] = []
        for tier in schedule:
            if not isinstance(tier, (list, tuple)) or len(tier) < 2:
                return None
            threshold = cls._number(tier[0])
            rate_percent = cls._number(tier[1], positive=True)
            if threshold is None or rate_percent is None:
                return None
            if threshold == 0:
                zero_volume_rates.append(rate_percent / 100.0)
        if len(zero_volume_rates) != 1:
            return None
        rate = zero_volume_rates[0]
        return rate if 0 < rate < 0.1 else None

    @classmethod
    def _activity_time(cls, activity: Dict[str, Any]) -> Optional[float]:
        for key in ("transaction_time", "timestamp", "date", "time"):
            parsed = cls._source_time(activity.get(key))
            if parsed is not None:
                return parsed
        return None

    @classmethod
    def _alpaca_fee_evidence(cls, client: Any, received_at: float) -> Optional[Dict[str, Any]]:
        """Derive the account's observed crypto fee rate from provider activities."""
        after = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat().replace("+00:00", "Z")
        try:
            fills = client.get_account_activities(
                activity_types="FILL", after=after, direction="desc", page_size=100
            )
            fees = client.get_account_activities(
                activity_types="CFEE", after=after, direction="desc", page_size=100
            )
        except Exception as exc:
            logger.debug("Alpaca fee evidence unavailable: %s", exc)
            return None
        if not isinstance(fills, list) or not fills or not isinstance(fees, list) or not fees:
            return None

        fee_notional = 0.0
        fee_symbols: Set[str] = set()
        event_times: List[float] = []
        for fee in fees:
            if not isinstance(fee, dict):
                return None
            symbol = fee.get("symbol")
            if not isinstance(symbol, str) or not symbol.strip():
                return None
            quantity = cls._number(fee.get("qty"))
            price = cls._number(fee.get("price"), positive=True)
            event_time = cls._activity_time(fee)
            if quantity is None or quantity == 0 or price is None or event_time is None:
                return None
            fee_notional += abs(quantity) * price
            fee_symbols.add(symbol.replace("/", "").upper())
            event_times.append(event_time)

        fill_notional = 0.0
        matching_fill_count = 0
        for fill in fills:
            if not isinstance(fill, dict):
                return None
            symbol = fill.get("symbol")
            if not isinstance(symbol, str) or not symbol.strip():
                return None
            if symbol.replace("/", "").upper() not in fee_symbols:
                continue
            quantity = cls._number(fill.get("qty"), positive=True)
            price = cls._number(fill.get("price"), positive=True)
            event_time = cls._activity_time(fill)
            if quantity is None or price is None or event_time is None:
                return None
            fill_notional += quantity * price
            matching_fill_count += 1
            event_times.append(event_time)

        if matching_fill_count == 0 or fill_notional <= 0 or fee_notional <= 0 or not event_times:
            return None
        source_timestamp = max(event_times)
        fee_rate = fee_notional / fill_notional
        if not (0 < fee_rate < 0.1) or not cls._fresh(source_timestamp, received_at, 31 * 24 * 60 * 60):
            return None
        return {
            "fee_rate": fee_rate,
            "source_id": "alpaca_account_activities_fill+cfee_30d",
            "source_timestamp": source_timestamp,
        }

    @classmethod
    def _build_opportunity(
        cls,
        *,
        symbol: str,
        exchange: str,
        region: str,
        momentum_pct: float,
        confidence_scale_pct: float,
        quote: Dict[str, float],
        fee_rate: float,
        volume: float,
        source: str,
        reason: str,
        source_id: str,
        source_timestamp: float,
        received_at: float,
        field_provenance: Dict[str, Any],
        min_momentum_pct: float,
    ) -> Optional[GlobalOpportunity]:
        numeric_values = (
            momentum_pct,
            confidence_scale_pct,
            fee_rate,
            volume,
            source_timestamp,
            received_at,
            quote.get("bid"),
            quote.get("ask"),
            quote.get("mid"),
            quote.get("spread_decimal"),
        )
        if (
            not symbol
            or exchange not in {"kraken", "alpaca"}
            or not source_id
            or not field_provenance
            or not all(isinstance(value, (int, float)) and math.isfinite(float(value)) for value in numeric_values)
            or abs(momentum_pct) < min_momentum_pct
            or confidence_scale_pct <= 0
            or fee_rate <= 0
            or volume <= 0
            or quote["mid"] <= 0
            or quote["spread_decimal"] < 0
            or not cls._fresh(source_timestamp, received_at, 2 * 60 * 60)
        ):
            return None

        round_trip_cost = fee_rate * 2.0 + quote["spread_decimal"]
        net_edge = abs(momentum_pct) / 100.0 - round_trip_cost
        if not math.isfinite(net_edge) or net_edge <= 0:
            return None
        direction = "buy" if momentum_pct > 0 else "sell"
        entry_price = quote["ask"] if direction == "buy" else quote["bid"]
        return GlobalOpportunity(
            symbol=symbol,
            exchange=exchange,
            region=region,
            direction=direction,
            momentum_pct=momentum_pct,
            confidence=min(abs(momentum_pct) / confidence_scale_pct, 1.0),
            current_price=quote["mid"],
            entry_price=entry_price,
            fee_pct=fee_rate,
            spread_pct=quote["spread_decimal"],
            net_edge=net_edge,
            source=source,
            reason=reason,
            volume=volume,
            truth_status="real_derived",
            source_id=source_id,
            source_timestamp=source_timestamp,
            received_at=received_at,
            generated_values=False,
            eligible_for_external_action=True,
            field_provenance=field_provenance,
        )
        
    def _init_exchanges(self):
        """Initialize connections to all exchanges."""
        print("\n🦈🌍 ORCA GLOBAL HUNTER INITIALIZING...")
        print("=" * 60)
        
        # Kraken (24/7 crypto)
        try:
            from aureon.exchanges.kraken_client import get_kraken_client
            self.exchanges['kraken'] = get_kraken_client()
            if self.exchanges['kraken']:
                pairs = self.exchanges['kraken']._load_asset_pairs()
                self.universes['kraken'] = {p for p in pairs.keys() if not p.endswith('.d')}
                print(f"   🐙 KRAKEN: {len(self.universes['kraken'])} pairs")
        except Exception as e:
            logger.warning(f"Kraken init error: {e}")
            
        # Alpaca (crypto + stocks)
        try:
            from aureon.exchanges.alpaca_client import AlpacaClient
            self.exchanges['alpaca'] = AlpacaClient()
            
            # Crypto universe
            crypto = self.exchanges['alpaca'].list_assets(status='active', asset_class='crypto') or []
            self.universes['alpaca_crypto'] = set()
            for a in crypto:
                sym = a.get('symbol') if isinstance(a, dict) else getattr(a, 'symbol', None)
                if sym:
                    if '/' not in sym:
                        sym = f"{sym}/USD"
                    self.universes['alpaca_crypto'].add(sym)
            print(f"   🦙 ALPACA CRYPTO: {len(self.universes['alpaca_crypto'])} symbols")
            
            # Stock universe (if market hours)
            if self._is_stock_market_open():
                try:
                    from alpaca.trading.requests import GetAssetsRequest
                    from alpaca.trading.enums import AssetClass, AssetStatus
                    
                    api = self.exchanges['alpaca'].trading_client
                    if api:
                        request = GetAssetsRequest(
                            asset_class=AssetClass.US_EQUITY,
                            status=AssetStatus.ACTIVE
                        )
                        assets = api.get_all_assets(request)
                        tradeable = [a for a in assets if a.tradable]
                        self.universes['alpaca_stocks'] = {a.symbol for a in tradeable[:1000]}  # Top 1000
                        print(f"   📈 ALPACA STOCKS: {len(self.universes['alpaca_stocks'])} symbols (market open)")
                except Exception as e:
                    logger.debug(f"Stock universe error: {e}")
                    
        except Exception as e:
            logger.warning(f"Alpaca init error: {e}")
            
        # Binance (data only for UK)
        try:
            from aureon.exchanges.binance_client import BinanceClient, get_binance_client
            self.exchanges['binance'] = BinanceClient()
            info = self.exchanges['binance'].exchange_info()
            symbols = [s['symbol'] for s in info.get('symbols', []) if s.get('status') == 'TRADING']
            self.universes['binance'] = set(symbols)
            print(f"   🟡 BINANCE: {len(self.universes['binance'])} pairs (data only)")
        except Exception as e:
            logger.warning(f"Binance init error: {e}")
            
        # Calculate total
        total = sum(len(u) for u in self.universes.values())
        print(f"\n   🌍 TOTAL HUNTING GROUNDS: {total:,} opportunities!")
        print("=" * 60)
        
    def _is_stock_market_open(self) -> bool:
        """Check if US stock market is open."""
        now = datetime.now(timezone.utc)
        # Mon-Fri 14:30-21:00 UTC (9:30am-4pm EST)
        if now.weekday() < 5:
            hour = now.hour + now.minute / 60
            return 14.5 <= hour < 21
        return False
        
    def get_active_sessions(self) -> List[MarketSession]:
        """Get currently active market sessions."""
        return [s for s in MARKET_SESSIONS if s.is_active()]
        
    def scan_kraken(self, limit: int = 100) -> List[GlobalOpportunity]:
        """
        🐙 Scan Kraken for momentum opportunities.
        
        Kraken has 1,419 pairs - we sample the most active ones.
        """
        opportunities: List[GlobalOpportunity] = []
        kraken = self.exchanges.get("kraken")
        if kraken is None:
            return opportunities

        try:
            usd_pairs = sorted(
                pair for pair in self.universes.get("kraken", set())
                if "USD" in pair.upper() and "USDC" not in pair.upper() and "USDT" not in pair.upper()
            )[:limit]
            if not usd_pairs:
                return opportunities
            pairs = kraken._load_asset_pairs(force=True)
            tickers = kraken._ticker(usd_pairs)
            provider_timestamp = self._kraken_server_time(kraken)
            received_at = time.time()
            if (
                not isinstance(pairs, dict)
                or not isinstance(tickers, dict)
                or provider_timestamp is None
                or not self._fresh(provider_timestamp, received_at, 2 * 60 * 60)
            ):
                return opportunities

            for internal, ticker in tickers.items():
                if not isinstance(ticker, dict):
                    continue
                pair_info = pairs.get(internal)
                if not isinstance(pair_info, dict):
                    pair_info = self._kraken_pair_info(kraken, str(internal), pairs)
                if not isinstance(pair_info, dict):
                    continue
                symbol = str(pair_info.get("wsname") or pair_info.get("altname") or internal)
                if "USD" not in symbol.upper() or "USDC" in symbol.upper() or "USDT" in symbol.upper():
                    continue

                close_values = ticker.get("c")
                bid_values = ticker.get("b")
                ask_values = ticker.get("a")
                volume_values = ticker.get("v")
                if (
                    not isinstance(close_values, (list, tuple)) or not close_values
                    or not isinstance(bid_values, (list, tuple)) or not bid_values
                    or not isinstance(ask_values, (list, tuple)) or not ask_values
                    or not isinstance(volume_values, (list, tuple)) or len(volume_values) < 2
                ):
                    continue
                last_price = self._number(close_values[0], positive=True)
                open_price = self._number(ticker.get("o"), positive=True)
                base_volume = self._number(volume_values[1], positive=True)
                quote = self._quote_metrics(bid_values[0], ask_values[0])
                fee_rate = self._kraken_fee_rate(pair_info)
                if None in (last_price, open_price, base_volume, quote, fee_rate):
                    continue
                momentum = ((last_price - open_price) / open_price) * 100.0
                quote_volume = base_volume * last_price
                provenance = {
                    "prices": {
                        "source_id": "kraken_public_ticker",
                        "source_timestamp": provider_timestamp,
                        "fields": ["c", "b", "a"],
                    },
                    "momentum_pct": {
                        "truth_status": "real_derived",
                        "source_id": "kraken_public_ticker:c+o",
                        "source_timestamp": provider_timestamp,
                    },
                    "fee_pct": {
                        "source_id": "kraken_public_asset_pairs:fees_zero_volume_tier",
                        "source_timestamp": provider_timestamp,
                    },
                    "spread_pct": {
                        "truth_status": "real_derived",
                        "source_id": "kraken_public_ticker:b+a",
                        "source_timestamp": provider_timestamp,
                    },
                    "volume": {
                        "truth_status": "real_derived",
                        "source_id": "kraken_public_ticker:v_24h*c",
                        "source_timestamp": provider_timestamp,
                    },
                    "net_edge": {
                        "truth_status": "real_derived",
                        "inputs": ["momentum_pct", "fee_pct", "spread_pct"],
                    },
                }
                opportunity = self._build_opportunity(
                    symbol=symbol,
                    exchange="kraken",
                    region="GLOBAL",
                    momentum_pct=momentum,
                    confidence_scale_pct=5.0,
                    quote=quote,
                    fee_rate=fee_rate,
                    volume=quote_volume,
                    source="kraken_momentum",
                    reason=f"Kraken provider 24h momentum {momentum:+.2f}%",
                    source_id="kraken_public_ticker+asset_pairs+time",
                    source_timestamp=provider_timestamp,
                    received_at=received_at,
                    field_provenance=provenance,
                    min_momentum_pct=self.min_momentum_pct,
                )
                if opportunity is not None:
                    opportunities.append(opportunity)
        except Exception as exc:
            logger.warning("Kraken scan error: %s", exc)

        return opportunities
        
    def scan_alpaca_crypto(self) -> List[GlobalOpportunity]:
        """
        🦙 Scan Alpaca crypto for momentum opportunities.
        """
        opportunities: List[GlobalOpportunity] = []
        alpaca = self.exchanges.get("alpaca")
        if alpaca is None:
            return opportunities

        try:
            fee_evidence = self._alpaca_fee_evidence(alpaca, time.time())
            if fee_evidence is None:
                logger.warning("Alpaca scan blocked: provider fee activities are unavailable")
                return opportunities

            for symbol in sorted(self.universes.get("alpaca_crypto", set())):
                try:
                    compact_symbol = str(symbol).replace("/", "").upper()
                    base_symbol = compact_symbol[:-3] if compact_symbol.endswith("USD") else compact_symbol
                    if not base_symbol:
                        continue
                    normalized = f"{base_symbol}/USD"
                    quotes = alpaca.get_latest_crypto_quotes([normalized])
                    quote_payload = quotes.get(normalized) if isinstance(quotes, dict) else None
                    if not isinstance(quote_payload, dict):
                        continue
                    quote = self._quote_metrics(quote_payload.get("bp"), quote_payload.get("ap"))
                    quote_timestamp = self._source_time(quote_payload.get("t"))
                    if quote is None or quote_timestamp is None:
                        continue

                    bars_response = alpaca.get_crypto_bars([normalized], timeframe="1Hour", limit=25)
                    bars_by_symbol = bars_response.get("bars") if isinstance(bars_response, dict) else None
                    bars = bars_by_symbol.get(normalized) if isinstance(bars_by_symbol, dict) else None
                    if not isinstance(bars, list) or len(bars) < 24:
                        continue

                    parsed_bars: List[Dict[str, float]] = []
                    malformed = False
                    for bar in bars[-24:]:
                        if not isinstance(bar, dict):
                            malformed = True
                            break
                        event_time = self._source_time(bar.get("t"))
                        open_price = self._number(bar.get("o"), positive=True)
                        high_price = self._number(bar.get("h"), positive=True)
                        low_price = self._number(bar.get("l"), positive=True)
                        close_price = self._number(bar.get("c"), positive=True)
                        base_volume = self._number(bar.get("v"))
                        if (
                            None in (event_time, open_price, high_price, low_price, close_price, base_volume)
                            or base_volume < 0
                            or high_price < max(open_price, close_price, low_price)
                            or low_price > min(open_price, close_price, high_price)
                        ):
                            malformed = True
                            break
                        parsed_bars.append({
                            "timestamp": event_time,
                            "open": open_price,
                            "close": close_price,
                            "volume": base_volume,
                        })
                    if malformed or len(parsed_bars) < 24:
                        continue
                    if any(
                        current["timestamp"] <= previous["timestamp"]
                        for previous, current in zip(parsed_bars, parsed_bars[1:])
                    ):
                        continue
                    window_seconds = parsed_bars[-1]["timestamp"] - parsed_bars[0]["timestamp"]
                    if not 20 * 60 * 60 <= window_seconds <= 27 * 60 * 60:
                        continue

                    received_at = time.time()
                    source_timestamp = min(quote_timestamp, parsed_bars[-1]["timestamp"])
                    if not self._fresh(source_timestamp, received_at, 2 * 60 * 60):
                        continue
                    open_24h = parsed_bars[0]["open"]
                    momentum = ((quote["mid"] - open_24h) / open_24h) * 100.0
                    quote_volume = sum(bar["volume"] * bar["close"] for bar in parsed_bars)
                    provenance = {
                        "prices": {
                            "source_id": "alpaca_crypto_latest_quotes",
                            "source_timestamp": quote_timestamp,
                            "fields": ["bp", "ap"],
                        },
                        "momentum_pct": {
                            "truth_status": "real_derived",
                            "source_id": "alpaca_crypto_hour_bars:o+latest_quotes:bp+ap",
                            "source_timestamp": source_timestamp,
                        },
                        "fee_pct": {
                            "truth_status": "real_derived",
                            "source_id": fee_evidence["source_id"],
                            "source_timestamp": fee_evidence["source_timestamp"],
                        },
                        "spread_pct": {
                            "truth_status": "real_derived",
                            "source_id": "alpaca_crypto_latest_quotes:bp+ap",
                            "source_timestamp": quote_timestamp,
                        },
                        "volume": {
                            "truth_status": "real_derived",
                            "source_id": "alpaca_crypto_hour_bars:v*c",
                            "source_timestamp": parsed_bars[-1]["timestamp"],
                        },
                        "net_edge": {
                            "truth_status": "real_derived",
                            "inputs": ["momentum_pct", "fee_pct", "spread_pct"],
                        },
                    }
                    opportunity = self._build_opportunity(
                        symbol=normalized,
                        exchange="alpaca",
                        region="AMERICAS",
                        momentum_pct=momentum,
                        confidence_scale_pct=5.0,
                        quote=quote,
                        fee_rate=fee_evidence["fee_rate"],
                        volume=quote_volume,
                        source="alpaca_crypto",
                        reason=f"Alpaca provider rolling 24h momentum {momentum:+.2f}%",
                        source_id="alpaca_crypto_quotes+hour_bars+account_fee_activities",
                        source_timestamp=source_timestamp,
                        received_at=received_at,
                        field_provenance=provenance,
                        min_momentum_pct=self.min_momentum_pct,
                    )
                    if opportunity is not None:
                        opportunities.append(opportunity)
                except Exception as exc:
                    logger.debug("Alpaca %s error: %s", symbol, exc)
        except Exception as exc:
            logger.warning("Alpaca crypto scan error: %s", exc)

        return opportunities
        
    def scan_binance(self, limit: int = 500) -> List[GlobalOpportunity]:
        """
        🟡 Scan Binance for momentum (data only - UK restricted).
        
        We use Binance's massive universe to FIND opportunities,
        then execute on Kraken/Alpaca where the same pair exists.
        """
        opportunities: List[GlobalOpportunity] = []

        try:
            import requests

            response = requests.get("https://api.binance.com/api/v3/ticker/24hr", timeout=10)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                return opportunities
            binance_received_at = time.time()

            kraken = self.exchanges.get("kraken")
            kraken_pairs: Dict[str, Any] = {}
            kraken_trade_map: Dict[str, str] = {}
            if kraken is not None:
                try:
                    loaded_pairs = kraken._load_asset_pairs(force=True)
                    if isinstance(loaded_pairs, dict):
                        kraken_pairs = loaded_pairs
                        for internal, pair_info in kraken_pairs.items():
                            compact = self._kraken_canonical_compact(pair_info)
                            if compact:
                                kraken_trade_map[compact] = str(pair_info.get("altname") or internal)
                except Exception as exc:
                    logger.debug("Kraken pair evidence unavailable: %s", exc)
            alpaca_universe = {
                str(symbol).replace("/", "").upper(): str(symbol)
                for symbol in self.universes.get("alpaca_crypto", set())
            }
            candidates: List[Dict[str, Any]] = []
            for ticker in payload:
                if not isinstance(ticker, dict):
                    continue
                source_symbol = ticker.get("symbol")
                if not isinstance(source_symbol, str) or not source_symbol.endswith("USDT"):
                    continue
                last_price = self._number(ticker.get("lastPrice"), positive=True)
                momentum = self._number(ticker.get("priceChangePercent"))
                volume = self._number(ticker.get("quoteVolume"), positive=True)
                source_timestamp = self._source_time(ticker.get("closeTime"))
                if None in (last_price, momentum, volume, source_timestamp):
                    continue
                if (
                    abs(momentum) < self.min_momentum_pct
                    or volume < 100_000
                    or not self._fresh(source_timestamp, binance_received_at, 2 * 60 * 60)
                ):
                    continue

                base = source_symbol[:-4]
                compact_target = f"{base}USD"
                if compact_target in kraken_trade_map:
                    exchange = "kraken"
                elif compact_target in alpaca_universe:
                    exchange = "alpaca"
                else:
                    continue
                candidates.append({
                    "source_symbol": source_symbol,
                    "target_symbol": f"{base}/USD",
                    "compact_target": compact_target,
                    "execution_request_symbol": kraken_trade_map.get(compact_target),
                    "exchange": exchange,
                    "signal_price": last_price,
                    "momentum": momentum,
                    "volume": volume,
                    "source_timestamp": source_timestamp,
                })
            candidates.sort(key=lambda candidate: abs(candidate["momentum"]), reverse=True)
            candidates = candidates[:limit]
            if not candidates:
                return opportunities

            target_evidence: Dict[Tuple[str, str], Dict[str, Any]] = {}
            kraken_candidates = [item for item in candidates if item["exchange"] == "kraken"]
            if kraken is not None and kraken_candidates:
                try:
                    pairs = kraken_pairs
                    requested = sorted({item["execution_request_symbol"] for item in kraken_candidates})
                    raw_tickers: Dict[str, Any] = {}
                    for offset in range(0, len(requested), 40):
                        batch = kraken._ticker(requested[offset:offset + 40])
                        if not isinstance(batch, dict):
                            raw_tickers = {}
                            break
                        raw_tickers.update(batch)
                    provider_timestamp = self._kraken_server_time(kraken)
                    target_received_at = time.time()
                    if (
                        isinstance(pairs, dict)
                        and raw_tickers
                        and provider_timestamp is not None
                        and self._fresh(provider_timestamp, target_received_at, 2 * 60 * 60)
                    ):
                        for internal, ticker in raw_tickers.items():
                            if not isinstance(ticker, dict):
                                continue
                            pair_info = pairs.get(internal)
                            if not isinstance(pair_info, dict):
                                pair_info = self._kraken_pair_info(kraken, str(internal), pairs)
                            if not isinstance(pair_info, dict):
                                continue
                            bids = ticker.get("b")
                            asks = ticker.get("a")
                            if (
                                not isinstance(bids, (list, tuple)) or not bids
                                or not isinstance(asks, (list, tuple)) or not asks
                            ):
                                continue
                            quote = self._quote_metrics(bids[0], asks[0])
                            fee_rate = self._kraken_fee_rate(pair_info)
                            if quote is None or fee_rate is None:
                                continue
                            canonical = self._kraken_canonical_compact(pair_info)
                            if canonical:
                                target_evidence[("kraken", canonical)] = {
                                    "quote": quote,
                                    "fee_rate": fee_rate,
                                    "source_id": "kraken_public_ticker+asset_pairs+time",
                                    "source_timestamp": provider_timestamp,
                                    "fee_source_timestamp": provider_timestamp,
                                    "received_at": target_received_at,
                                }
                except Exception as exc:
                    logger.debug("Kraken execution evidence unavailable: %s", exc)

            alpaca = self.exchanges.get("alpaca")
            alpaca_candidates = [item for item in candidates if item["exchange"] == "alpaca"]
            if alpaca is not None and alpaca_candidates:
                try:
                    fee_evidence = self._alpaca_fee_evidence(alpaca, time.time())
                    symbols = sorted({item["target_symbol"] for item in alpaca_candidates})
                    quotes = alpaca.get_latest_crypto_quotes(symbols)
                    target_received_at = time.time()
                    if fee_evidence is not None and isinstance(quotes, dict):
                        for symbol in symbols:
                            quote_payload = quotes.get(symbol)
                            if not isinstance(quote_payload, dict):
                                continue
                            quote = self._quote_metrics(quote_payload.get("bp"), quote_payload.get("ap"))
                            source_timestamp = self._source_time(quote_payload.get("t"))
                            if (
                                quote is None
                                or source_timestamp is None
                                or not self._fresh(source_timestamp, target_received_at, 2 * 60 * 60)
                            ):
                                continue
                            target_evidence[("alpaca", symbol.replace("/", "").upper())] = {
                                "quote": quote,
                                "fee_rate": fee_evidence["fee_rate"],
                                "source_id": "alpaca_crypto_latest_quotes+account_fee_activities",
                                "source_timestamp": source_timestamp,
                                "fee_source_timestamp": fee_evidence["source_timestamp"],
                                "received_at": target_received_at,
                            }
                except Exception as exc:
                    logger.debug("Alpaca execution evidence unavailable: %s", exc)

            for candidate in candidates:
                evidence = target_evidence.get((candidate["exchange"], candidate["compact_target"]))
                if not isinstance(evidence, dict):
                    continue
                received_at = max(binance_received_at, evidence["received_at"])
                source_timestamp = min(candidate["source_timestamp"], evidence["source_timestamp"])
                provenance = {
                    "prices": {
                        "source_id": evidence["source_id"],
                        "source_timestamp": evidence["source_timestamp"],
                        "note": "execution-venue bid and ask",
                    },
                    "momentum_pct": {
                        "truth_status": "live",
                        "source_id": "binance_public_ticker_24hr:priceChangePercent",
                        "source_timestamp": candidate["source_timestamp"],
                    },
                    "fee_pct": {
                        "truth_status": "real_derived",
                        "source_id": evidence["source_id"],
                        "source_timestamp": evidence["fee_source_timestamp"],
                    },
                    "spread_pct": {
                        "truth_status": "real_derived",
                        "source_id": evidence["source_id"],
                        "source_timestamp": evidence["source_timestamp"],
                    },
                    "volume": {
                        "truth_status": "live",
                        "source_id": "binance_public_ticker_24hr:quoteVolume",
                        "source_timestamp": candidate["source_timestamp"],
                    },
                    "net_edge": {
                        "truth_status": "real_derived",
                        "inputs": ["momentum_pct", "fee_pct", "spread_pct"],
                    },
                    "signal_reference_price": {
                        "value": candidate["signal_price"],
                        "source_id": "binance_public_ticker_24hr:lastPrice",
                        "source_timestamp": candidate["source_timestamp"],
                    },
                }
                opportunity = self._build_opportunity(
                    symbol=candidate["target_symbol"],
                    exchange=candidate["exchange"],
                    region="GLOBAL",
                    momentum_pct=candidate["momentum"],
                    confidence_scale_pct=10.0,
                    quote=evidence["quote"],
                    fee_rate=evidence["fee_rate"],
                    volume=candidate["volume"],
                    source="binance_signal",
                    reason=(
                        f"Binance provider 24h momentum {candidate['momentum']:+.2f}% "
                        f"with quote volume ${candidate['volume'] / 1_000_000:.1f}M"
                    ),
                    source_id=f"binance_public_ticker_24hr+{evidence['source_id']}",
                    source_timestamp=source_timestamp,
                    received_at=received_at,
                    field_provenance=provenance,
                    min_momentum_pct=self.min_momentum_pct,
                )
                if opportunity is not None:
                    opportunities.append(opportunity)
        except Exception as exc:
            logger.warning("Binance scan error: %s", exc)

        return opportunities
        
    def hunt_global(self) -> List[GlobalOpportunity]:
        """
        🦈🌍 HUNT THE ENTIRE GLOBE
        
        Scans ALL exchanges in parallel and returns the best opportunities.
        """
        print("\n" + "=" * 70)
        print("🦈🌍 ORCA GLOBAL HUNT - SCANNING THE WORLD 🌍🦈")
        print("=" * 70)
        
        # Show active sessions
        active = self.get_active_sessions()
        print(f"\n🌐 ACTIVE MARKET SESSIONS:")
        for session in active:
            print(f"   {session.region}: {session.name} ({', '.join(session.exchanges)})")
        
        all_opportunities = []
        
        # Scan all exchanges in parallel
        print(f"\n🔍 SCANNING ALL EXCHANGES...")
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(self.scan_kraken, 200): 'kraken',
                executor.submit(self.scan_alpaca_crypto): 'alpaca',
                executor.submit(self.scan_binance, 300): 'binance',
            }
            
            for future in as_completed(futures):
                exchange = futures[future]
                try:
                    opps = future.result()
                    all_opportunities.extend(opps)
                    print(f"   {exchange.upper()}: Found {len(opps)} momentum signals")
                except Exception as e:
                    print(f"   {exchange.upper()}: Error - {e}")
                    
        # Sort by net edge (most profitable first)
        all_opportunities.sort(key=lambda x: x.net_edge, reverse=True)
        
        # Update stats
        self.total_scanned = sum(len(u) for u in self.universes.values())
        self.scan_count += 1
        self.opportunities = all_opportunities
        
        # Summary
        print(f"\n📊 GLOBAL SCAN RESULTS:")
        print(f"   Universe scanned: {self.total_scanned:,} symbols")
        print(f"   Momentum signals: {len(all_opportunities)}")
        
        if all_opportunities:
            print(f"\n🎯 TOP OPPORTUNITIES:")
            for opp in all_opportunities[:10]:
                print(f"   {opp.symbol} ({opp.exchange}): {opp.momentum_pct:+.2f}% "
                      f"→ net edge {opp.net_edge*100:.3f}%")
                      
        print("=" * 70)
        
        return all_opportunities
        
    def get_best_kill(self) -> Optional[GlobalOpportunity]:
        """Get the single best opportunity for immediate execution."""
        if not self.opportunities:
            self.hunt_global()
            
        profitable = [o for o in self.opportunities if o.is_profitable]
        if profitable:
            return profitable[0]
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# 🦈 QUICK FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def orca_hunt_world():
    """🦈🌍 Hunt the entire global market."""
    hunter = OrcaGlobalHunter()
    return hunter.hunt_global()

def orca_best_global_kill():
    """🦈🎯 Get the single best global opportunity."""
    hunter = OrcaGlobalHunter()
    return hunter.get_best_kill()

def orca_global_status():
    """🌍 Show current global market status."""
    print("\n" + "=" * 60)
    print("🌍 GLOBAL MARKET STATUS")
    print("=" * 60)
    
    now = datetime.now(timezone.utc)
    print(f"\n⏰ Current UTC: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    print(f"\n📍 ACTIVE SESSIONS:")
    for session in MARKET_SESSIONS:
        status = "🟢 ACTIVE" if session.is_active() else "⚫ CLOSED"
        print(f"   {status} {session.name} ({session.region}) - {', '.join(session.exchanges)}")
        
    print(f"\n🪙 CRYPTO: 24/7 ALWAYS ACTIVE")
    print(f"   Kraken: 1,419 pairs")
    print(f"   Alpaca: 62 symbols")
    print(f"   Binance: 1,565 pairs (data)")
    
    print("=" * 60)


if __name__ == "__main__":
    # Run global hunt
    opportunities = orca_hunt_world()
    
    if opportunities:
        print(f"\n🦈 READY TO STRIKE!")
        best = opportunities[0]
        print(f"   Best target: {best.symbol} on {best.exchange}")
        print(f"   Direction: {best.direction.upper()}")
        print(f"   Momentum: {best.momentum_pct:+.2f}%")
        print(f"   Net edge: {best.net_edge*100:.3f}%")
    else:
        print("\n⏳ No profitable opportunities found - scanning continues...")
