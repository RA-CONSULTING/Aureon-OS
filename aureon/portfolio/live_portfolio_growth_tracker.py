#!/usr/bin/env python3
"""
🔴 LIVE PORTFOLIO GROWTH TRACKER 🔴
Records growth evidence only from complete, fresh provider-valued portfolios.

Tracks:
- Total portfolio value (USD)
- P&L since start
- Growth % and ROI
- Per-exchange breakdowns
- Position-by-position details
- Historical snapshots for proof
- Live streaming updates

Integrates with: Black Box, Orca, Queen, Auris
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys, os
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        def _is_utf8_wrapper(stream):
            """Check if stream is already a UTF-8 TextIOWrapper."""
            return (isinstance(stream, io.TextIOWrapper) and 
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        def _is_buffer_valid(stream):
            """Check if stream buffer is valid and not closed."""
            if not hasattr(stream, 'buffer'):
                return False
            try:
                return stream.buffer is not None and not stream.buffer.closed
            except (ValueError, AttributeError):
                return False
        # Only wrap if not already UTF-8 wrapped AND buffer is valid
        if _is_buffer_valid(sys.stdout) and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        if _is_buffer_valid(sys.stderr) and not _is_utf8_wrapper(sys.stderr):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

import asyncio
import json
import math
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Sacred constants
PHI = (1 + math.sqrt(5)) / 2  # 1.618033989 - Golden Ratio
PERFECTION_ANGLE = 306.0  # 360 - 54 (golden angle complement)

# Import exchange clients
try:
    from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
except ImportError:
    KrakenClient = None

try:
    from aureon.exchanges.alpaca_client import AlpacaClient
except ImportError:
    AlpacaClient = None

# Try to import Queen + Auris consciousness
try:
    from aureon.wisdom.metatron_probability_billion_path import QueenAurisPingPong
    CONSCIOUSNESS_AVAILABLE = True
except ImportError:
    CONSCIOUSNESS_AVAILABLE = False


@dataclass
class PriceObservation:
    """A provider price receipt or an explicit USD unit conversion."""
    asset: str
    exchange: str
    price_usd: Optional[float]
    truth_status: str
    source_id: str
    source_timestamp: Optional[float]
    received_at: float
    age_seconds: Optional[float]
    freshness_basis: str
    is_fresh: bool
    generated_values: bool = False
    reason: Optional[str] = None

    @property
    def is_usable(self) -> bool:
        return (
            self.price_usd is not None
            and math.isfinite(self.price_usd)
            and self.price_usd > 0.0
            and self.is_fresh
            and not self.generated_values
            and self.truth_status in {"live", "real_derived"}
        )


@dataclass
class AssetHolding:
    """Single asset holding on an exchange."""
    asset: str
    exchange: str
    quantity: float
    usd_value: Optional[float]
    current_price: Optional[float]
    cost_basis: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    valuation_method: str = "provider_quote"
    truth_status: str = "no_data"
    source_id: str = ""
    source_timestamp: Optional[float] = None
    received_at: Optional[float] = None
    age_seconds: Optional[float] = None
    freshness_basis: str = ""
    generated_values: bool = False
    reason: Optional[str] = None


@dataclass
class ExchangeSnapshot:
    """Snapshot of one exchange's portfolio."""
    exchange: str
    timestamp: float
    total_usd_value: Optional[float]
    holdings: List[AssetHolding] = field(default_factory=list)
    num_positions: int = 0
    largest_position_usd: float = 0.0
    largest_position_asset: str = ""
    valuation_status: str = "no_data"
    truth_status: str = "no_data"
    source_id: str = ""
    source_timestamp: Optional[float] = None
    received_at: Optional[float] = None
    max_source_age_seconds: Optional[float] = None
    freshness_basis: str = ""
    generated_values: bool = False
    unpriced_assets: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    cash_usd: Optional[float] = None


@dataclass
class PortfolioSnapshot:
    """Complete portfolio snapshot across all exchanges."""
    timestamp: float
    datetime_str: str
    total_usd_value: Optional[float]
    initial_usd_value: Optional[float]
    pnl_usd: Optional[float]
    growth_pct: Optional[float]
    roi_pct: Optional[float]
    exchanges: List[ExchangeSnapshot] = field(default_factory=list)
    num_exchanges: int = 0
    num_total_positions: int = 0
    largest_holding_usd: float = 0.0
    largest_holding_asset: str = ""
    largest_holding_exchange: str = ""
    
    # Sacred geometry
    sacred_alignment: Optional[float] = None  # How aligned with Fibonacci levels
    geometric_angle: Optional[float] = None  # Current angle in sacred geometry
    perfection_score: Optional[float] = None  # Distance from 306°
    valuation_status: str = "no_data"
    truth_status: str = "no_data"
    source_ids: List[str] = field(default_factory=list)
    source_timestamp: Optional[float] = None
    received_at: Optional[float] = None
    max_source_age_seconds: Optional[float] = None
    generated_values: bool = False
    incomplete_exchanges: List[str] = field(default_factory=list)
    proof_eligible: bool = False
    reason: Optional[str] = None
    schema_version: int = 2


@dataclass
class GrowthProof:
    """Historical proof of growth over time."""
    snapshots: List[PortfolioSnapshot] = field(default_factory=list)
    start_time: float = 0.0
    start_value: float = 0.0
    peak_value: float = 0.0
    peak_time: float = 0.0
    current_value: float = 0.0
    total_pnl: float = 0.0
    total_growth_pct: float = 0.0
    avg_growth_per_minute: float = 0.0
    sacred_growth_factor: float = 1.0  # Relationship to PHI
    truth_status: str = "no_data"
    generated_values: bool = False
    last_source_ids: List[str] = field(default_factory=list)
    last_source_timestamp: Optional[float] = None


class LivePortfolioTracker:
    """
    Live portfolio tracker that proves growth in real-time.
    
    Connects to all exchanges, tracks balance changes, calculates P&L,
    and maintains historical proof of portfolio growth.
    """
    
    def __init__(self):
        """Initialize portfolio tracker."""
        self.exchanges: Dict[str, Any] = {}
        self.initial_snapshot: Optional[PortfolioSnapshot] = None
        self.growth_proof = GrowthProof()
        self.consciousness = None
        try:
            configured_age = float(os.getenv("AUREON_PORTFOLIO_MAX_DATA_AGE_SECONDS", "60"))
        except (TypeError, ValueError):
            configured_age = 60.0
        self.max_data_age_seconds = max(1.0, configured_age)
        
        # Proof storage
        self.proof_file = Path("portfolio_growth_proof.json")
        self.snapshot_file = Path("portfolio_snapshots.json")
        
        # Load historical data if exists
        self._load_historical_proof()
        
        print("🔴 LIVE PORTFOLIO GROWTH TRACKER INITIALIZING...")
        
    def _load_historical_proof(self):
        """Load only proof written under the provider-provenance contract."""
        if self.proof_file.exists():
            try:
                with open(self.proof_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if (
                        data.get('schema_version') != 2
                        or data.get('valuation_status') != 'complete'
                        or data.get('truth_status') != 'real_derived'
                        or data.get('generated_values') is not False
                    ):
                        print("   Historical growth proof ignored: missing live provider provenance")
                        return
                    start_value = self._as_finite_float(data.get('start_value'))
                    if start_value is None or start_value <= 0.0:
                        print("   Historical growth proof ignored: invalid provider-valued baseline")
                        return
                    self.growth_proof.start_time = data.get('start_time', 0.0)
                    self.growth_proof.start_value = start_value
                    self.growth_proof.peak_value = data.get('peak_value', 0.0)
                    self.growth_proof.peak_time = data.get('peak_time', 0.0)
                    self.growth_proof.current_value = data.get('current_value', 0.0)
                    self.growth_proof.total_pnl = data.get('total_pnl', 0.0)
                    self.growth_proof.total_growth_pct = data.get('total_growth_pct', 0.0)
                    self.growth_proof.avg_growth_per_minute = data.get('avg_growth_per_minute', 0.0)
                    self.growth_proof.sacred_growth_factor = data.get('sacred_growth_factor', 1.0)
                    self.growth_proof.truth_status = 'real_derived'
                    self.growth_proof.generated_values = False
                    self.growth_proof.last_source_ids = list(data.get('source_ids') or [])
                    self.growth_proof.last_source_timestamp = self._as_finite_float(
                        data.get('source_timestamp')
                    )
                    print(f"📊 Loaded historical proof: Start ${self.growth_proof.start_value:,.2f}")
            except Exception as e:
                print(f"⚠️  Could not load historical proof: {e}")

    @staticmethod
    def _as_finite_float(value: Any) -> Optional[float]:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if math.isfinite(number) else None

    @staticmethod
    def _provider_timestamp(payload: Any) -> Optional[float]:
        """Extract, but never invent, a provider timestamp from a payload."""
        if not isinstance(payload, dict):
            return None
        candidates: List[Any] = []
        for key in ('source_timestamp', 'timestamp', 'time', 'ts', 't'):
            if key in payload:
                candidates.append(payload.get(key))
        last = payload.get('last')
        if isinstance(last, dict):
            for key in ('source_timestamp', 'timestamp', 'time', 'ts', 't'):
                if key in last:
                    candidates.append(last.get(key))
        for candidate in candidates:
            if candidate is None or isinstance(candidate, bool):
                continue
            numeric = LivePortfolioTracker._as_finite_float(candidate)
            if numeric is not None:
                if numeric > 10_000_000_000:
                    numeric /= 1000.0
                return numeric
            if isinstance(candidate, str):
                try:
                    parsed = datetime.fromisoformat(candidate.replace('Z', '+00:00'))
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=timezone.utc)
                    return parsed.timestamp()
                except ValueError:
                    continue
        return None
    
    def _save_proof(self) -> bool:
        """Save growth proof to disk."""
        if (
            self.growth_proof.truth_status != 'real_derived'
            or self.growth_proof.generated_values
            or self.growth_proof.start_value <= 0.0
        ):
            return False
        try:
            proof_data = {
                'schema_version': 2,
                'valuation_status': 'complete',
                'truth_status': self.growth_proof.truth_status,
                'generated_values': self.growth_proof.generated_values,
                'start_time': self.growth_proof.start_time,
                'start_value': self.growth_proof.start_value,
                'peak_value': self.growth_proof.peak_value,
                'peak_time': self.growth_proof.peak_time,
                'current_value': self.growth_proof.current_value,
                'total_pnl': self.growth_proof.total_pnl,
                'total_growth_pct': self.growth_proof.total_growth_pct,
                'avg_growth_per_minute': self.growth_proof.avg_growth_per_minute,
                'sacred_growth_factor': self.growth_proof.sacred_growth_factor,
                'source_ids': self.growth_proof.last_source_ids,
                'source_timestamp': self.growth_proof.last_source_timestamp,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            with open(self.proof_file, 'w', encoding='utf-8') as f:
                json.dump(proof_data, f, indent=2)
            with open(self.proof_file, 'r', encoding='utf-8') as f:
                readback = json.load(f)
            return (
                readback.get('schema_version') == 2
                and readback.get('truth_status') == 'real_derived'
                and readback.get('generated_values') is False
                and readback.get('source_ids') == self.growth_proof.last_source_ids
            )
        except Exception as e:
            print(f"⚠️  Could not save proof: {e}")
            return False
    
    def _save_snapshot(self, snapshot: PortfolioSnapshot) -> bool:
        """Save snapshot to historical record."""
        if (
            not snapshot.proof_eligible
            or snapshot.valuation_status != 'complete'
            or snapshot.truth_status != 'real_derived'
            or snapshot.generated_values
        ):
            return False
        try:
            snapshots = []
            if self.snapshot_file.exists():
                with open(self.snapshot_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    if isinstance(loaded, list):
                        snapshots = [
                            item
                            for item in loaded
                            if (
                                isinstance(item, dict)
                                and item.get('schema_version') == 2
                                and item.get('valuation_status') == 'complete'
                                and item.get('truth_status') == 'real_derived'
                                and item.get('generated_values') is False
                                and item.get('proof_eligible') is True
                            )
                        ]
            
            # Add new snapshot
            snapshots.append(asdict(snapshot))
            
            # Keep last 1000 snapshots
            if len(snapshots) > 1000:
                snapshots = snapshots[-1000:]
            
            with open(self.snapshot_file, 'w', encoding='utf-8') as f:
                json.dump(snapshots, f, indent=2)
            with open(self.snapshot_file, 'r', encoding='utf-8') as f:
                readback = json.load(f)
            return (
                isinstance(readback, list)
                and bool(readback)
                and readback[-1].get('schema_version') == 2
                and readback[-1].get('truth_status') == 'real_derived'
                and readback[-1].get('generated_values') is False
            )
        except Exception as e:
            print(f"⚠️  Could not save snapshot: {e}")
            return False
    
    async def initialize_exchanges(self):
        """Initialize all exchange connections."""
        print("\n🔗 Connecting to exchanges...")
        
        # Kraken
        if KrakenClient:
            try:
                self.exchanges['kraken'] = get_kraken_client()
                print("   ✅ Kraken client initialized; provider read pending")
            except Exception as e:
                print(f"   ⚠️  Kraken: {e}")
        
        # Alpaca
        if AlpacaClient:
            try:
                self.exchanges['alpaca'] = AlpacaClient()
                print("   ✅ Alpaca client initialized; provider read pending")
            except Exception as e:
                print(f"   ⚠️  Alpaca: {e}")
        
        if not self.exchanges:
            print("   ⚠️  NO_DATA: no exchange clients initialized")
        
        # Initialize consciousness if available
        if CONSCIOUSNESS_AVAILABLE:
            try:
                self.consciousness = QueenAurisPingPong()
                print("   ✅ Queen + Auris consciousness active")
            except Exception as e:
                print(f"   ⚠️  Consciousness: {e}")
    
    @staticmethod
    def _normalize_asset(asset: str) -> str:
        raw = str(asset or '').strip().upper()
        aliases = {
            'ZUSD': 'USD',
            'XXBT': 'BTC',
            'XBT': 'BTC',
            'XETH': 'ETH',
            'XXRP': 'XRP',
            'XXLM': 'XLM',
        }
        return aliases.get(raw, raw)

    def _freshness(
        self,
        payload: Any,
        received_at: float,
    ) -> tuple[Optional[float], Optional[float], str, bool]:
        source_timestamp = self._provider_timestamp(payload)
        if source_timestamp is None:
            return None, 0.0, 'provider_response_received_at', True
        raw_age = received_at - source_timestamp
        is_fresh = -5.0 <= raw_age <= self.max_data_age_seconds
        return source_timestamp, max(0.0, raw_age), 'provider_source_timestamp', is_fresh

    def _no_data_price(
        self,
        asset: str,
        exchange: str,
        reason: str,
        *,
        source_id: str = '',
        received_at: Optional[float] = None,
        source_timestamp: Optional[float] = None,
        age_seconds: Optional[float] = None,
        freshness_basis: str = '',
    ) -> PriceObservation:
        return PriceObservation(
            asset=self._normalize_asset(asset),
            exchange=exchange,
            price_usd=None,
            truth_status='no_data',
            source_id=source_id,
            source_timestamp=source_timestamp,
            received_at=received_at if received_at is not None else time.time(),
            age_seconds=age_seconds,
            freshness_basis=freshness_basis,
            is_fresh=False,
            generated_values=False,
            reason=reason,
        )

    async def get_asset_price_observation(
        self,
        asset: str,
        exchange: str,
    ) -> PriceObservation:
        """Read a USD price from the provider with explicit freshness."""
        clean_asset = self._normalize_asset(asset)
        received_at = time.time()

        if clean_asset == 'USD':
            return PriceObservation(
                asset=clean_asset,
                exchange=exchange,
                price_usd=1.0,
                truth_status='real_derived',
                source_id='usd_denomination_unit_conversion',
                source_timestamp=None,
                received_at=received_at,
                age_seconds=0.0,
                freshness_basis='unit_conversion',
                is_fresh=True,
                generated_values=False,
                reason='USD amount denominated in USD; not a market-price observation',
            )

        client = self.exchanges.get(exchange)
        source_id = f"{exchange}.get_ticker:{clean_asset}/USD"
        if client is None:
            return self._no_data_price(
                clean_asset, exchange, 'exchange client unavailable', source_id=source_id
            )
        if bool(getattr(client, 'dry_run', False)) or bool(getattr(client, 'use_paper', False)):
            return self._no_data_price(
                clean_asset,
                exchange,
                'non-production exchange mode cannot value live holdings',
                source_id=source_id,
            )
        if not hasattr(client, 'get_ticker'):
            return self._no_data_price(
                clean_asset, exchange, 'provider ticker method unavailable', source_id=source_id
            )

        try:
            ticker = client.get_ticker(f"{clean_asset}/USD")
            received_at = time.time()
        except Exception as exc:
            return self._no_data_price(
                clean_asset,
                exchange,
                f"provider ticker read failed: {type(exc).__name__}",
                source_id=source_id,
                received_at=time.time(),
            )

        if not isinstance(ticker, dict):
            return self._no_data_price(
                clean_asset,
                exchange,
                'provider ticker response is not a mapping',
                source_id=source_id,
                received_at=received_at,
            )

        candidates: List[Any] = [ticker.get('price'), ticker.get('lastPrice')]
        last = ticker.get('last')
        if isinstance(last, dict):
            candidates.extend([last.get('price'), last.get('last')])
        else:
            candidates.append(last)
        price = next(
            (
                parsed
                for parsed in (self._as_finite_float(candidate) for candidate in candidates)
                if parsed is not None and parsed > 0.0
            ),
            None,
        )
        source_timestamp, age_seconds, freshness_basis, is_fresh = self._freshness(
            ticker, received_at
        )
        if price is None:
            return self._no_data_price(
                clean_asset,
                exchange,
                'provider ticker contained no positive finite USD price',
                source_id=source_id,
                received_at=received_at,
                source_timestamp=source_timestamp,
                age_seconds=age_seconds,
                freshness_basis=freshness_basis,
            )
        if not is_fresh:
            return self._no_data_price(
                clean_asset,
                exchange,
                'provider ticker is stale or future-dated',
                source_id=source_id,
                received_at=received_at,
                source_timestamp=source_timestamp,
                age_seconds=age_seconds,
                freshness_basis=freshness_basis,
            )
        return PriceObservation(
            asset=clean_asset,
            exchange=exchange,
            price_usd=price,
            truth_status='live',
            source_id=source_id,
            source_timestamp=source_timestamp,
            received_at=received_at,
            age_seconds=age_seconds,
            freshness_basis=freshness_basis,
            is_fresh=True,
            generated_values=False,
        )

    async def get_asset_price(self, asset: str, exchange: str) -> Optional[float]:
        """Compatibility helper returning None when no usable provider price exists."""
        observation = await self.get_asset_price_observation(asset, exchange)
        return observation.price_usd if observation.is_usable else None
    
    async def get_exchange_snapshot(self, exchange_name: str, client: Any) -> ExchangeSnapshot:
        """Get portfolio snapshot from one exchange."""
        received_at = time.time()
        snapshot = ExchangeSnapshot(
            exchange=exchange_name,
            timestamp=received_at,
            total_usd_value=None,
            source_id=f"{exchange_name}.account",
            received_at=received_at,
        )

        if client is None:
            snapshot.errors.append('exchange client unavailable')
            return snapshot
        if bool(getattr(client, 'dry_run', False)) or bool(getattr(client, 'use_paper', False)):
            snapshot.errors.append('non-production exchange mode cannot create growth proof')
            return snapshot

        try:
            if exchange_name == 'alpaca':
                account = client.get_account()
                received_at = time.time()
                snapshot.timestamp = received_at
                snapshot.received_at = received_at
                if not isinstance(account, dict) or 'equity' not in account:
                    snapshot.errors.append('provider account response missing equity')
                    return snapshot
                equity = self._as_finite_float(account.get('equity'))
                if equity is None or equity < 0.0:
                    snapshot.errors.append('provider account equity is not a non-negative finite value')
                    return snapshot
                source_timestamp, age_seconds, freshness_basis, is_fresh = self._freshness(
                    account, received_at
                )
                snapshot.source_id = 'alpaca.get_account:equity'
                snapshot.source_timestamp = source_timestamp
                snapshot.max_source_age_seconds = age_seconds
                snapshot.freshness_basis = freshness_basis
                snapshot.cash_usd = self._as_finite_float(account.get('cash'))
                if not is_fresh:
                    snapshot.errors.append('provider account response is stale or future-dated')
                    return snapshot
                # Alpaca equity already includes cash and positions. Adding cash again
                # would double-count the account.
                snapshot.total_usd_value = equity
                snapshot.valuation_status = 'complete'
                snapshot.truth_status = 'live'
                return snapshot

            if exchange_name == 'kraken':
                balances = client.get_account_balance()
            else:
                snapshot.errors.append('unsupported exchange valuation adapter')
                return snapshot

            received_at = time.time()
            snapshot.timestamp = received_at
            snapshot.received_at = received_at
            snapshot.source_id = 'kraken.get_account_balance'
            snapshot.freshness_basis = 'provider_response_received_at'
            snapshot.max_source_age_seconds = 0.0
            if not isinstance(balances, dict) or not balances:
                snapshot.errors.append('provider balance response empty or unavailable')
                return snapshot

            priced_total = 0.0
            source_timestamps: List[float] = []
            source_ages: List[float] = []
            for asset, quantity in balances.items():
                parsed_quantity = self._as_finite_float(quantity)
                if parsed_quantity is None or parsed_quantity < 0.0:
                    snapshot.unpriced_assets.append(str(asset))
                    snapshot.errors.append(f"{asset}: invalid provider quantity")
                    continue
                if parsed_quantity <= 0.0001:
                    continue
                observation = await self.get_asset_price_observation(asset, exchange_name)
                if not observation.is_usable:
                    snapshot.unpriced_assets.append(str(asset))
                    snapshot.holdings.append(
                        AssetHolding(
                            asset=str(asset),
                            exchange=exchange_name,
                            quantity=parsed_quantity,
                            usd_value=None,
                            current_price=None,
                            valuation_method='provider_quote',
                            truth_status='no_data',
                            source_id=observation.source_id,
                            source_timestamp=observation.source_timestamp,
                            received_at=observation.received_at,
                            age_seconds=observation.age_seconds,
                            freshness_basis=observation.freshness_basis,
                            generated_values=False,
                            reason=observation.reason,
                        )
                    )
                    continue

                price = observation.price_usd
                assert price is not None
                usd_value = parsed_quantity * price
                holding = AssetHolding(
                    asset=str(asset),
                    exchange=exchange_name,
                    quantity=parsed_quantity,
                    usd_value=usd_value,
                    current_price=price,
                    valuation_method=(
                        'usd_unit_conversion'
                        if observation.source_id == 'usd_denomination_unit_conversion'
                        else 'provider_quote'
                    ),
                    truth_status=observation.truth_status,
                    source_id=observation.source_id,
                    source_timestamp=observation.source_timestamp,
                    received_at=observation.received_at,
                    age_seconds=observation.age_seconds,
                    freshness_basis=observation.freshness_basis,
                    generated_values=False,
                    reason=observation.reason,
                )
                snapshot.holdings.append(holding)
                priced_total += usd_value
                if observation.source_timestamp is not None:
                    source_timestamps.append(observation.source_timestamp)
                if observation.age_seconds is not None:
                    source_ages.append(observation.age_seconds)
                if usd_value > snapshot.largest_position_usd:
                    snapshot.largest_position_usd = usd_value
                    snapshot.largest_position_asset = str(asset)

            snapshot.num_positions = len(snapshot.holdings)
            snapshot.source_timestamp = min(source_timestamps) if source_timestamps else None
            snapshot.max_source_age_seconds = max(source_ages) if source_ages else 0.0
            if snapshot.unpriced_assets or snapshot.errors:
                snapshot.valuation_status = 'incomplete'
                snapshot.truth_status = 'no_data'
                snapshot.total_usd_value = None
            else:
                snapshot.valuation_status = 'complete'
                snapshot.truth_status = 'real_derived'
                snapshot.total_usd_value = priced_total
        except Exception as e:
            snapshot.errors.append(f"provider account read failed: {type(e).__name__}")
            snapshot.valuation_status = 'no_data'
            snapshot.truth_status = 'no_data'
            snapshot.total_usd_value = None
            print(f"⚠️  Error getting {exchange_name} snapshot: {e}")

        return snapshot
    
    def calculate_sacred_alignment(self, value: float) -> tuple[float, float, float]:
        """
        Calculate sacred geometry alignment.
        
        Returns: (sacred_alignment, geometric_angle, perfection_score)
        """
        # Fibonacci levels
        fib_levels = [0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272, 1.618, 2.618]
        
        # Find closest Fibonacci ratio in growth
        if self.growth_proof.start_value > 0:
            growth_ratio = value / self.growth_proof.start_value
        else:
            growth_ratio = 1.0
        
        # Find closest Fibonacci level
        closest_fib = min(fib_levels, key=lambda x: abs(x - growth_ratio))
        alignment = 1.0 - abs(closest_fib - growth_ratio) / closest_fib
        
        # Map to geometric angle
        # Use Fibonacci level to interpolate toward 306°
        if growth_ratio < 1.0:
            angle = 180.0 + (growth_ratio * 60)  # 180-240° range for losses
        else:
            # Map growth above 1.0 toward 306°
            excess = min((growth_ratio - 1.0) / PHI, 1.0)  # Cap at 1.0
            angle = 240.0 + (excess * 66.0)  # 240-306° range
        
        # Calculate perfection score (distance from 306°)
        angle_distance = abs(angle - PERFECTION_ANGLE)
        perfection_score = max(0.0, 1.0 - (angle_distance / 180.0))  # 0-1 scale
        
        return alignment, angle, perfection_score
    
    async def get_full_portfolio_snapshot(self) -> PortfolioSnapshot:
        """Get complete portfolio snapshot across all exchanges."""
        received_at = time.time()
        snapshot = PortfolioSnapshot(
            timestamp=received_at,
            datetime_str=datetime.now(timezone.utc).isoformat(),
            total_usd_value=None,
            initial_usd_value=(
                self.growth_proof.start_value
                if self.growth_proof.start_value > 0.0
                else None
            ),
            pnl_usd=None,
            growth_pct=None,
            roi_pct=None,
            received_at=received_at,
        )

        if not self.exchanges:
            snapshot.reason = 'no exchange clients initialized'
            return snapshot

        valued_total = 0.0
        source_timestamps: List[float] = []
        source_ages: List[float] = []
        # Get snapshots from all exchanges
        for exchange_name, client in self.exchanges.items():
            exchange_snapshot = await self.get_exchange_snapshot(exchange_name, client)
            snapshot.exchanges.append(exchange_snapshot)
            snapshot.num_total_positions += exchange_snapshot.num_positions
            if exchange_snapshot.source_id:
                snapshot.source_ids.append(exchange_snapshot.source_id)
            snapshot.source_ids.extend(
                holding.source_id
                for holding in exchange_snapshot.holdings
                if holding.source_id
            )
            if exchange_snapshot.source_timestamp is not None:
                source_timestamps.append(exchange_snapshot.source_timestamp)
            if exchange_snapshot.max_source_age_seconds is not None:
                source_ages.append(exchange_snapshot.max_source_age_seconds)
            if (
                exchange_snapshot.valuation_status != 'complete'
                or exchange_snapshot.total_usd_value is None
                or exchange_snapshot.generated_values
            ):
                snapshot.incomplete_exchanges.append(exchange_name)
            else:
                valued_total += exchange_snapshot.total_usd_value
            
            # Track largest holding globally
            if exchange_snapshot.largest_position_usd > snapshot.largest_holding_usd:
                snapshot.largest_holding_usd = exchange_snapshot.largest_position_usd
                snapshot.largest_holding_asset = exchange_snapshot.largest_position_asset
                snapshot.largest_holding_exchange = exchange_name
        
        snapshot.num_exchanges = len(snapshot.exchanges)
        snapshot.source_ids = sorted(set(snapshot.source_ids))
        snapshot.source_timestamp = min(source_timestamps) if source_timestamps else None
        snapshot.max_source_age_seconds = max(source_ages) if source_ages else 0.0

        if snapshot.incomplete_exchanges:
            snapshot.valuation_status = 'incomplete'
            snapshot.truth_status = 'no_data'
            snapshot.reason = (
                'portfolio valuation incomplete: '
                + ', '.join(sorted(snapshot.incomplete_exchanges))
            )
            return snapshot

        snapshot.total_usd_value = valued_total
        snapshot.valuation_status = 'complete'
        snapshot.truth_status = 'real_derived'
        snapshot.proof_eligible = True

        if self.growth_proof.start_value > 0.0:
            snapshot.pnl_usd = valued_total - self.growth_proof.start_value
            snapshot.growth_pct = (
                snapshot.pnl_usd / self.growth_proof.start_value
            ) * 100.0
            snapshot.roi_pct = snapshot.growth_pct

        sacred_alignment, geometric_angle, perfection_score = self.calculate_sacred_alignment(
            valued_total
        )
        snapshot.sacred_alignment = sacred_alignment
        snapshot.geometric_angle = geometric_angle
        snapshot.perfection_score = perfection_score
        
        return snapshot
    
    def update_growth_proof(self, snapshot: PortfolioSnapshot) -> bool:
        """Persist growth proof only from a complete provider-valued snapshot."""
        total_value = self._as_finite_float(snapshot.total_usd_value)
        if (
            not snapshot.proof_eligible
            or snapshot.valuation_status != 'complete'
            or snapshot.truth_status != 'real_derived'
            or snapshot.generated_values
            or total_value is None
            or total_value < 0.0
        ):
            print(f"⚠️  NO_DATA: growth proof not updated ({snapshot.reason or 'incomplete valuation'})")
            return False

        # Initialize start values if needed
        if self.growth_proof.start_value <= 0.0:
            if total_value <= 0.0:
                print("⚠️  NO_DATA: a positive provider-valued baseline is required for growth proof")
                return False
            self.growth_proof.start_time = snapshot.timestamp
            self.growth_proof.start_value = total_value

        snapshot.initial_usd_value = self.growth_proof.start_value
        snapshot.pnl_usd = total_value - self.growth_proof.start_value
        snapshot.growth_pct = (snapshot.pnl_usd / self.growth_proof.start_value) * 100.0
        snapshot.roi_pct = snapshot.growth_pct
        
        # Update current values
        self.growth_proof.current_value = total_value
        self.growth_proof.total_pnl = snapshot.pnl_usd
        self.growth_proof.total_growth_pct = snapshot.growth_pct
        self.growth_proof.truth_status = 'real_derived'
        self.growth_proof.generated_values = False
        self.growth_proof.last_source_ids = list(snapshot.source_ids)
        self.growth_proof.last_source_timestamp = snapshot.source_timestamp
        
        # Track peak
        if total_value > self.growth_proof.peak_value:
            self.growth_proof.peak_value = total_value
            self.growth_proof.peak_time = snapshot.timestamp
        
        # Calculate growth rate
        elapsed_minutes = (snapshot.timestamp - self.growth_proof.start_time) / 60.0
        if elapsed_minutes > 0:
            self.growth_proof.avg_growth_per_minute = self.growth_proof.total_pnl / elapsed_minutes
        
        # Calculate sacred growth factor (relationship to PHI)
        if self.growth_proof.start_value > 0:
            growth_multiple = total_value / self.growth_proof.start_value
            # How close to PHI-based growth?
            phi_target = PHI  # 1.618 is first PHI target
            self.growth_proof.sacred_growth_factor = growth_multiple / phi_target
        
        # Add to snapshots
        self.growth_proof.snapshots.append(snapshot)
        
        # Save proof
        proof_saved = self._save_proof()
        snapshot_saved = self._save_snapshot(snapshot)
        if not (proof_saved and snapshot_saved):
            print("⚠️  Growth proof write could not be verified by disk read-back")
        return proof_saved and snapshot_saved
    
    def display_snapshot(self, snapshot: PortfolioSnapshot):
        """Display portfolio snapshot with beautiful formatting."""
        print("\n" + "="*80)
        print(f"📊 LIVE PORTFOLIO SNAPSHOT - {snapshot.datetime_str}")
        print("="*80)

        print(f"\n🔎 VALUATION STATUS: {snapshot.valuation_status.upper()}")
        if snapshot.total_usd_value is None:
            print("💰 TOTAL PORTFOLIO VALUE: NO_DATA")
            if snapshot.reason:
                print(f"   Reason: {snapshot.reason}")
        else:
            print(f"💰 TOTAL PORTFOLIO VALUE: ${snapshot.total_usd_value:,.2f}")
        if snapshot.source_ids:
            print(f"   Sources: {', '.join(snapshot.source_ids)}")
        print(f"   Generated values: {snapshot.generated_values}")

        if (
            snapshot.initial_usd_value is not None
            and snapshot.initial_usd_value > 0
            and snapshot.pnl_usd is not None
            and snapshot.growth_pct is not None
            and snapshot.roi_pct is not None
        ):
            print(f"\n📈 GROWTH METRICS:")
            print(f"   Starting Value: ${snapshot.initial_usd_value:,.2f}")
            print(f"   Current Value:  ${snapshot.total_usd_value:,.2f}")
            print(f"   P&L:            ${snapshot.pnl_usd:+,.2f}")
            print(f"   Growth:         {snapshot.growth_pct:+.2f}%")
            print(f"   ROI:            {snapshot.roi_pct:+.2f}%")
        
        if (
            snapshot.sacred_alignment is not None
            and snapshot.geometric_angle is not None
            and snapshot.perfection_score is not None
        ):
            print(f"\n🔮 SACRED GEOMETRY:")
            print(f"   Alignment:      {snapshot.sacred_alignment*100:.1f}%")
            print(f"   Angle:          {snapshot.geometric_angle:.1f}°")
            print(f"   Perfection:     {snapshot.perfection_score*100:.1f}% (Target: 306°)")
        
        print(f"\n📊 PORTFOLIO COMPOSITION:")
        print(f"   Exchanges:      {snapshot.num_exchanges}")
        print(f"   Total Positions: {snapshot.num_total_positions}")
        if snapshot.largest_holding_asset:
            print(f"   Largest Holding: {snapshot.largest_holding_asset} @ {snapshot.largest_holding_exchange}")
            print(f"                   ${snapshot.largest_holding_usd:,.2f}")
        
        # Per-exchange breakdown
        print(f"\n💼 EXCHANGE BREAKDOWN:")
        for ex_snapshot in snapshot.exchanges:
            if ex_snapshot.total_usd_value is None:
                print(f"\n   {ex_snapshot.exchange.upper()}: NO_DATA ({ex_snapshot.valuation_status})")
            else:
                print(f"\n   {ex_snapshot.exchange.upper()}: ${ex_snapshot.total_usd_value:,.2f}")
            print(f"   Positions: {ex_snapshot.num_positions}")
            if ex_snapshot.unpriced_assets:
                print(f"   Unpriced: {', '.join(ex_snapshot.unpriced_assets)}")
            for error in ex_snapshot.errors:
                print(f"   Error: {error}")
            
            # Show top 3 holdings
            sorted_holdings = sorted(
                ex_snapshot.holdings,
                key=lambda x: x.usd_value if x.usd_value is not None else -1.0,
                reverse=True,
            )
            for holding in sorted_holdings[:3]:
                if holding.usd_value is None or holding.current_price is None:
                    print(f"      {holding.asset}: {holding.quantity:.4f} @ NO_DATA")
                else:
                    print(f"      {holding.asset}: {holding.quantity:.4f} @ ${holding.current_price:.2f} = ${holding.usd_value:,.2f}")
    
    def display_growth_proof(self):
        """Display historical growth proof."""
        print("\n" + "="*80)
        print("🏆 GROWTH PROOF - HISTORICAL PERFORMANCE")
        print("="*80)
        
        proof = self.growth_proof
        if proof.truth_status != 'real_derived' or proof.start_value <= 0.0:
            print("\nNO_DATA: no complete provider-valued growth proof is available")
            return
        
        print(f"\n⏱️  TIME PERIOD:")
        if proof.start_time > 0:
            start_dt = datetime.fromtimestamp(proof.start_time).strftime("%Y-%m-%d %H:%M:%S")
            elapsed_minutes = (time.time() - proof.start_time) / 60.0
            print(f"   Start: {start_dt}")
            print(f"   Duration: {elapsed_minutes:.1f} minutes")
        
        print(f"\n💰 CAPITAL GROWTH:")
        print(f"   Starting Value:  ${proof.start_value:,.2f}")
        print(f"   Current Value:   ${proof.current_value:,.2f}")
        print(f"   Peak Value:      ${proof.peak_value:,.2f}")
        print(f"   Total P&L:       ${proof.total_pnl:+,.2f}")
        print(f"   Total Growth:    {proof.total_growth_pct:+.2f}%")
        
        if proof.avg_growth_per_minute != 0:
            print(f"\n📊 GROWTH RATE:")
            print(f"   Per Minute:      ${proof.avg_growth_per_minute:+,.2f}")
            print(f"   Per Hour:        ${proof.avg_growth_per_minute * 60:+,.2f}")
            print(f"   Per Day:         ${proof.avg_growth_per_minute * 1440:+,.2f}")
        
        print(f"\n🔮 SACRED METRICS:")
        print(f"   Growth Factor:   {proof.sacred_growth_factor:.4f}× (φ = {PHI:.4f})")
        if proof.sacred_growth_factor >= 1.0:
            print(f"   Status:          ✨ EXCEEDING GOLDEN RATIO TARGET ✨")
        else:
            remaining = (1.0 - proof.sacred_growth_factor) * 100
            print(f"   Status:          {remaining:.1f}% to φ target")
        
        print(f"\n📈 SNAPSHOT HISTORY:")
        print(f"   Total Snapshots: {len(proof.snapshots)}")
        if len(proof.snapshots) >= 2:
            recent = proof.snapshots[-5:]  # Last 5
            print(f"   Recent Values:")
            for snap in recent:
                dt = datetime.fromtimestamp(snap.timestamp).strftime("%H:%M:%S")
                print(f"      {dt}: ${snap.total_usd_value:,.2f} ({snap.growth_pct:+.2f}%)")
    
    async def stream_live_updates(self, update_interval: float = 5.0, duration: float = 60.0):
        """
        Stream live portfolio updates.
        
        Args:
            update_interval: Seconds between updates
            duration: Total duration in seconds (0 = infinite)
        """
        print("\n🔴 STARTING LIVE PORTFOLIO STREAM...")
        print(f"   Update Interval: {update_interval}s")
        if duration > 0:
            print(f"   Duration: {duration}s")
        else:
            print(f"   Duration: INFINITE (Ctrl+C to stop)")
        
        start_time = time.time()
        update_count = 0
        
        try:
            while True:
                # Check duration
                if duration > 0 and (time.time() - start_time) >= duration:
                    break
                
                # Get snapshot
                snapshot = await self.get_full_portfolio_snapshot()
                
                # Update proof
                proof_updated = self.update_growth_proof(snapshot)
                
                # Display
                if update_count % 5 == 0:  # Full display every 5 updates
                    self.display_snapshot(snapshot)
                else:
                    # Quick update
                    if proof_updated:
                        print(f"\n⏱️  {snapshot.datetime_str} | ${snapshot.total_usd_value:,.2f} | P&L: ${snapshot.pnl_usd:+,.2f} ({snapshot.growth_pct:+.2f}%) | Perfection: {snapshot.perfection_score*100:.1f}%")
                    else:
                        print(f"\n⏱️  {snapshot.datetime_str} | NO_DATA | proof unchanged")
                
                update_count += 1
                
                # Wait for next update
                await asyncio.sleep(update_interval)
        
        except KeyboardInterrupt:
            print("\n\n⏹️  Stream stopped by user")
        
        # Final summary
        print("\n" + "="*80)
        print("🏁 LIVE STREAM COMPLETE")
        print("="*80)
        
        final_snapshot = await self.get_full_portfolio_snapshot()
        self.display_snapshot(final_snapshot)
        self.display_growth_proof()


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Live Portfolio Growth Tracker')
    parser.add_argument('--interval', type=float, default=5.0, help='Update interval in seconds')
    parser.add_argument('--duration', type=float, default=60.0, help='Total duration in seconds (0=infinite)')
    parser.add_argument('--snapshot-only', action='store_true', help='Take single snapshot and exit')
    
    args = parser.parse_args()
    
    # Create tracker
    tracker = LivePortfolioTracker()
    
    # Initialize exchanges
    await tracker.initialize_exchanges()
    
    if args.snapshot_only:
        # Single snapshot
        snapshot = await tracker.get_full_portfolio_snapshot()
        tracker.update_growth_proof(snapshot)
        tracker.display_snapshot(snapshot)
        tracker.display_growth_proof()
    else:
        # Live stream
        await tracker.stream_live_updates(
            update_interval=args.interval,
            duration=args.duration
        )


if __name__ == "__main__":
    asyncio.run(main())
