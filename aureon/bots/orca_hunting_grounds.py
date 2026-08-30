#!/usr/bin/env python3
"""
🦈🎯 ORCA HUNTING GROUNDS - Find the BEST Place to Hunt! 🎯🦈
═════════════════════════════════════════════════════════════════

This module analyzes all available exchanges and assets to find
the OPTIMAL hunting ground based on:

1. FEE STRUCTURE - Lower is better
2. SPREAD - Tighter is better  
3. VOLATILITY - Higher is better (need moves > fees)
4. LIQUIDITY - More is better (less slippage)

Gary Leckey | January 2026 | HUNT SMART, NOT HARD!
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
import os
import time
import math
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import logging

# UTF-8 fix
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

EVIDENCE_TTL_SECONDS = 60.0
RECEIPT_CLOCK_SKEW_SECONDS = 5.0


def _finite_number(value: object, *, positive: bool = False) -> Optional[float]:
    if isinstance(value, bool):
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


def _timestamp_epoch(value: object) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        epoch = float(value)
        return epoch if math.isfinite(epoch) else None
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    epoch = parsed.timestamp()
    return epoch if math.isfinite(epoch) else None


def _fresh_timestamp(value: object, now: float) -> Optional[str]:
    epoch = _timestamp_epoch(value)
    if epoch is None:
        return None
    if epoch > now + RECEIPT_CLOCK_SKEW_SECONDS:
        return None
    if now - epoch > EVIDENCE_TTL_SECONDS:
        return None
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat()


def _nonempty_text(value: object) -> Optional[str]:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


@dataclass
class HuntingGround:
    """A potential hunting ground (exchange + asset)."""
    exchange: str
    symbol: str
    price: float
    spread_pct: float
    fee_pct: float  # One-way taker fee
    volatility_1h: float  # 1-hour volatility estimate
    liquidity_score: float  # 0-1 liquidity rating
    source_id: str
    source_timestamp: str
    received_at: str
    market_receipt_id: str
    fee_source_id: str
    fee_source_timestamp: str
    fee_receipt_id: str
    truth_status: str = 'real_derived'
    data_origin: str = 'provider_market_and_account_receipts'
    provider_observation: bool = True
    operational_eligible: bool = True
    actionable: bool = True
    accounting_eligible: bool = False
    learning_eligible: bool = True
    generated_values: bool = False
    
    @property
    def round_trip_cost(self) -> float:
        """Total cost for a round trip trade."""
        return (self.fee_pct * 2) + self.spread_pct
    
    @property
    def profit_threshold(self) -> float:
        """Minimum % move needed to profit."""
        return self.round_trip_cost * 1.5  # 50% safety buffer
    
    @property
    def hunt_score(self) -> float:
        """
        Score this hunting ground (higher = better).
        
        Score = (Volatility - Cost) * Liquidity
        
        We want: High volatility, low cost, high liquidity
        """
        opportunity = self.volatility_1h - self.round_trip_cost
        if opportunity <= 0:
            return 0  # Can't profit here!
        return opportunity * self.liquidity_score * 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            'exchange': self.exchange,
            'symbol': self.symbol,
            'price': self.price,
            'spread_pct': self.spread_pct,
            'fee_pct': self.fee_pct,
            'volatility_1h': self.volatility_1h,
            'liquidity_score': self.liquidity_score,
            'round_trip_cost': self.round_trip_cost,
            'profit_threshold': self.profit_threshold,
            'hunt_score': self.hunt_score,
            'source_id': self.source_id,
            'source_timestamp': self.source_timestamp,
            'received_at': self.received_at,
            'market_receipt_id': self.market_receipt_id,
            'fee_source_id': self.fee_source_id,
            'fee_source_timestamp': self.fee_source_timestamp,
            'fee_receipt_id': self.fee_receipt_id,
            'truth_status': self.truth_status,
            'data_origin': self.data_origin,
            'provider_observation': self.provider_observation,
            'operational_eligible': self.operational_eligible,
            'actionable': self.actionable,
            'accounting_eligible': self.accounting_eligible,
            'learning_eligible': self.learning_eligible,
            'generated_values': self.generated_values,
        }
    
    def __str__(self):
        return (
            f"{self.exchange}:{self.symbol} | "
            f"Price: ${self.price:.2f} | "
            f"Spread: {self.spread_pct:.3f}% | "
            f"RT Cost: {self.round_trip_cost:.3f}% | "
            f"Vol: {self.volatility_1h:.2f}% | "
            f"Score: {self.hunt_score:.1f}"
        )


class OrcaHuntingGrounds:
    """
    🦈🎯 Find the BEST hunting grounds across all exchanges! 🎯🦈
    """
    
    def __init__(self):
        self.alpaca = None
        self.kraken = None
        self.binance = None
        self.last_no_data: List[Dict[str, Any]] = []
        
        self._init_clients()

    def _clear_no_data(self, exchange: str) -> None:
        self.last_no_data = [
            record
            for record in self.last_no_data
            if record.get('exchange') != exchange
        ]

    def _record_no_data(
        self,
        exchange: str,
        symbol: str,
        reason: str,
        observation: Optional[Dict[str, Any]] = None,
    ) -> None:
        observed = observation if isinstance(observation, dict) else {}
        self.last_no_data.append({
            'exchange': exchange,
            'symbol': symbol,
            'truth_status': 'no_data',
            'data_origin': 'unavailable',
            'reason': reason,
            'rejected_source_id': _nonempty_text(observed.get('source_id')),
            'rejected_source_timestamp': (
                _nonempty_text(observed.get('source_timestamp'))
                if isinstance(observed.get('source_timestamp'), str)
                else None
            ),
            'provider_observation': False,
            'generated_values': False,
            'operational_eligible': False,
            'action_eligible': False,
            'actionable': False,
            'accounting_eligible': False,
            'learning_eligible': False,
        })

    def _ground_from_observation(
        self,
        exchange: str,
        symbol: str,
        observation: object,
        received_at: float,
    ) -> Optional[HuntingGround]:
        if not isinstance(observation, dict):
            self._record_no_data(exchange, symbol, 'provider_observation_missing')
            return None
        if observation.get('generated_values') is not False:
            self._record_no_data(
                exchange,
                symbol,
                'provider_observation_generated_or_unstamped',
                observation,
            )
            return None
        if observation.get('truth_status') not in {
            'real_observation',
            'real_observed',
            'real_derived',
        }:
            self._record_no_data(
                exchange,
                symbol,
                'provider_truth_status_invalid',
                observation,
            )
            return None

        source_id = _nonempty_text(observation.get('source_id'))
        market_receipt_id = _nonempty_text(observation.get('market_receipt_id'))
        source_timestamp = _fresh_timestamp(
            observation.get('source_timestamp'),
            received_at,
        )
        fee_source_id = _nonempty_text(observation.get('fee_source_id'))
        fee_receipt_id = _nonempty_text(observation.get('fee_receipt_id'))
        fee_source_timestamp = _fresh_timestamp(
            observation.get('fee_source_timestamp'),
            received_at,
        )
        if (
            source_id is None
            or market_receipt_id is None
            or source_timestamp is None
            or fee_source_id is None
            or fee_receipt_id is None
            or fee_source_timestamp is None
            or observation.get('fee_generated_values') is not False
        ):
            self._record_no_data(
                exchange,
                symbol,
                'complete_fresh_market_and_fee_receipts_required',
                observation,
            )
            return None

        price = _finite_number(observation.get('price'), positive=True)
        bid = _finite_number(observation.get('bid'), positive=True)
        ask = _finite_number(observation.get('ask'), positive=True)
        volatility = _finite_number(observation.get('volatility_1h'))
        liquidity = _finite_number(observation.get('liquidity_score'))
        fee = _finite_number(observation.get('fee_pct'))
        if None in (price, bid, ask, volatility, liquidity, fee):
            self._record_no_data(
                exchange,
                symbol,
                'complete_finite_market_and_fee_values_required',
                observation,
            )
            return None
        assert price is not None
        assert bid is not None
        assert ask is not None
        assert volatility is not None
        assert liquidity is not None
        assert fee is not None
        if (
            bid > ask
            or price < bid
            or price > ask
            or volatility < 0
            or fee < 0
            or not 0 <= liquidity <= 1
        ):
            self._record_no_data(
                exchange,
                symbol,
                'market_or_fee_values_out_of_range',
                observation,
            )
            return None

        spread_pct = (ask - bid) / bid
        return HuntingGround(
            exchange=exchange,
            symbol=symbol,
            price=price,
            spread_pct=spread_pct,
            fee_pct=fee,
            volatility_1h=volatility,
            liquidity_score=liquidity,
            source_id=source_id,
            source_timestamp=source_timestamp,
            received_at=datetime.fromtimestamp(
                received_at,
                timezone.utc,
            ).isoformat(),
            market_receipt_id=market_receipt_id,
            fee_source_id=fee_source_id,
            fee_source_timestamp=fee_source_timestamp,
            fee_receipt_id=fee_receipt_id,
        )

    @staticmethod
    def _ground_remains_eligible(ground: object, now: float) -> bool:
        if not isinstance(ground, HuntingGround):
            return False
        return bool(
            ground.truth_status == 'real_derived'
            and ground.provider_observation is True
            and ground.generated_values is False
            and ground.operational_eligible is True
            and ground.actionable is True
            and ground.accounting_eligible is False
            and ground.learning_eligible is True
            and _nonempty_text(ground.source_id)
            and _nonempty_text(ground.market_receipt_id)
            and _nonempty_text(ground.fee_source_id)
            and _nonempty_text(ground.fee_receipt_id)
            and _fresh_timestamp(ground.source_timestamp, now)
            and _fresh_timestamp(ground.fee_source_timestamp, now)
        )
    
    def _init_clients(self):
        """Initialize exchange clients."""
        try:
            from aureon.exchanges.alpaca_client import AlpacaClient
            self.alpaca = AlpacaClient()
            logger.info("🦙 Alpaca connected")
        except Exception as e:
            logger.warning(f"Alpaca unavailable: {e}")
        
        try:
            from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
            self.kraken = get_kraken_client()
            logger.info("🦑 Kraken connected")
        except Exception as e:
            logger.warning(f"Kraken unavailable: {e}")
    
    def scan_alpaca(self) -> List[HuntingGround]:
        """Scan Alpaca for hunting opportunities."""
        grounds = []
        self._clear_no_data('alpaca')
        
        if not self.alpaca:
            self._record_no_data('alpaca', '*', 'provider_client_unavailable')
            return grounds
        
        # Major crypto pairs on Alpaca
        symbols = ['BTC/USD', 'ETH/USD', 'SOL/USD', 'DOGE/USD', 'AVAX/USD', 'LINK/USD']
        
        for symbol in symbols:
            try:
                ticker = self.alpaca.get_ticker(symbol)
                ground = self._ground_from_observation(
                    'alpaca',
                    symbol,
                    ticker,
                    time.time(),
                )
                if ground is not None:
                    grounds.append(ground)
                
            except Exception as e:
                self._record_no_data(
                    'alpaca',
                    symbol,
                    'provider_call_or_parse_failed',
                )
                logger.debug(f"Error scanning {symbol}: {e}")
        
        return grounds
    
    def scan_kraken(self) -> List[HuntingGround]:
        """Scan Kraken for hunting opportunities."""
        grounds = []
        self._clear_no_data('kraken')
        
        if not self.kraken:
            self._record_no_data('kraken', '*', 'provider_client_unavailable')
            return grounds
        
        # Major crypto pairs on Kraken
        pairs = [
            ('XBTUSD', 'BTC/USD'),
            ('ETHUSD', 'ETH/USD'),
            ('SOLUSD', 'SOL/USD'),
        ]
        
        for kraken_pair, display in pairs:
            try:
                ticker = self.kraken.get_24h_ticker(kraken_pair)
                ground = self._ground_from_observation(
                    'kraken',
                    display,
                    ticker,
                    time.time(),
                )
                if ground is not None:
                    grounds.append(ground)
                
            except Exception as e:
                self._record_no_data(
                    'kraken',
                    display,
                    'provider_call_or_parse_failed',
                )
                logger.debug(f"Error scanning {kraken_pair}: {e}")
        
        return grounds
    
    def find_best_grounds(self, min_score: float = 1.0) -> List[HuntingGround]:
        """
        Find all hunting grounds, ranked by score.
        
        Args:
            min_score: Minimum hunt score to include
            
        Returns:
            List of HuntingGround sorted by score (best first)
        """
        all_grounds = []
        
        # Scan all exchanges
        all_grounds.extend(self.scan_alpaca())
        all_grounds.extend(self.scan_kraken())
        
        # Recheck provenance immediately before anything can be ranked.
        viable = []
        now = time.time()
        for ground in all_grounds:
            if not self._ground_remains_eligible(ground, now):
                if isinstance(ground, HuntingGround):
                    self._record_no_data(
                        ground.exchange,
                        ground.symbol,
                        'opportunity_provenance_missing_or_expired',
                    )
                continue
            if ground.hunt_score >= min_score:
                viable.append(ground)
        
        # Sort by score (highest first)
        viable.sort(key=lambda g: g.hunt_score, reverse=True)
        
        return viable
    
    def get_best_ground(self) -> Optional[HuntingGround]:
        """Get the single best hunting ground right now."""
        grounds = self.find_best_grounds(min_score=0.5)
        return grounds[0] if grounds else None
    
    def print_analysis(self):
        """Print full hunting ground analysis."""
        print("=" * 80)
        print("🦈🎯 ORCA HUNTING GROUNDS ANALYSIS 🎯🦈")
        print("=" * 80)
        
        grounds = self.find_best_grounds(min_score=0)
        
        if not grounds:
            print("❌ No hunting grounds found!")
            return
        
        print()
        print(f"{'RANK':<5} {'EXCHANGE':<10} {'SYMBOL':<12} {'PRICE':>12} "
              f"{'SPREAD':>8} {'RT COST':>8} {'VOL':>6} {'SCORE':>8}")
        print("-" * 80)
        
        for i, g in enumerate(grounds[:10], 1):
            status = "✅" if g.hunt_score >= 1.5 else "⚠️" if g.hunt_score >= 0.5 else "❌"
            print(f"{status} {i:<3} {g.exchange:<10} {g.symbol:<12} ${g.price:>10.2f} "
                  f"{g.spread_pct*100:>7.3f}% {g.round_trip_cost*100:>7.3f}% "
                  f"{g.volatility_1h*100:>5.1f}% {g.hunt_score:>7.1f}")
        
        print()
        print("=" * 80)
        
        best = grounds[0]
        print(f"🎯 BEST HUNTING GROUND: {best.exchange.upper()} - {best.symbol}")
        print(f"   Round-trip cost: {best.round_trip_cost*100:.3f}%")
        print(f"   Min profit needed: {best.profit_threshold*100:.3f}%")
        print(f"   Est. hourly volatility: {best.volatility_1h*100:.1f}%")
        print(f"   HUNT SCORE: {best.hunt_score:.1f}")
        print("=" * 80)


def main():
    """Run hunting ground analysis."""
    hunter = OrcaHuntingGrounds()
    hunter.print_analysis()


if __name__ == "__main__":
    main()
