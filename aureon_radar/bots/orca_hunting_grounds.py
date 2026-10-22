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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

# UTF-8 fix
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class HuntingGround:
    """A potential hunting ground (exchange + asset)."""
    exchange: str
    symbol: str
    price: float
    spread_pct: float
    fee_pct: float  # One-way taker fee
    volatility_1h: float  # 1-hour volatility estimate (declared assumption)
    liquidity_score: float  # 0-1 liquidity rating
    change_24h_pct: float = None  # REAL 24h price change % when the venue provides it
    
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
    
    def __str__(self):
        return (
            f"{self.exchange}:{self.symbol} | "
            f"Price: ${self.price:.2f} | "
            f"Spread: {self.spread_pct:.3f}% | "
            f"RT Cost: {self.round_trip_cost:.3f}% | "
            f"Vol: {self.volatility_1h:.2f}% | "
            f"Score: {self.hunt_score:.1f}"
        )


# Fee profiles per exchange (taker fees)
EXCHANGE_FEES = {
    'alpaca': {
        'crypto': 0.0025,  # 0.25%
        'stock': 0.0,      # Commission free (but reg fees)
    },
    'kraken': {
        'crypto': 0.0026,  # 0.26%
    },
    'binance': {
        'crypto': 0.0010,  # 0.10% (region locked for UK)
    },
}


class OrcaHuntingGrounds:
    """
    🦈🎯 Find the BEST hunting grounds across all exchanges! 🎯🦈
    """
    
    def __init__(self):
        self.alpaca = None
        self.kraken = None
        self.binance = None
        
        self._init_clients()
    
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
        
        if not self.alpaca:
            return grounds
        
        # Major crypto pairs on Alpaca
        symbols = ['BTC/USD', 'ETH/USD', 'SOL/USD', 'DOGE/USD', 'AVAX/USD', 'LINK/USD']
        
        for symbol in symbols:
            try:
                ticker = self.alpaca.get_ticker(symbol)
                if not ticker:
                    continue
                
                price = float(ticker.get('price', 0) or ticker.get('last', 0) or 0)
                bid = float(ticker.get('bid', 0) or 0)
                ask = float(ticker.get('ask', 0) or 0)
                
                if price <= 0 or bid <= 0 or ask <= 0:
                    continue
                
                spread_pct = (ask - bid) / bid
                
                # Estimate volatility based on asset type
                vol_estimates = {
                    'BTC': 0.025,   # 2.5% avg hourly range
                    'ETH': 0.030,   # 3.0%
                    'SOL': 0.045,   # 4.5%
                    'DOGE': 0.050,  # 5.0%
                    'AVAX': 0.040,  # 4.0%
                    'LINK': 0.035,  # 3.5%
                }
                base = symbol.split('/')[0]
                vol = vol_estimates.get(base, 0.03)
                
                # Liquidity score (BTC/ETH best)
                liq_scores = {
                    'BTC': 0.95,
                    'ETH': 0.90,
                    'SOL': 0.75,
                    'DOGE': 0.70,
                    'AVAX': 0.65,
                    'LINK': 0.65,
                }
                liq = liq_scores.get(base, 0.5)
                
                ground = HuntingGround(
                    exchange='alpaca',
                    symbol=symbol,
                    price=price,
                    spread_pct=spread_pct,
                    fee_pct=EXCHANGE_FEES['alpaca']['crypto'],
                    volatility_1h=vol,
                    liquidity_score=liq
                )
                grounds.append(ground)
                
            except Exception as e:
                logger.debug(f"Error scanning {symbol}: {e}")
        
        return grounds
    
    def scan_kraken(self) -> List[HuntingGround]:
        """Scan Kraken for hunting opportunities."""
        grounds = []

        if not self.kraken:
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
                if not ticker:
                    continue

                # The upstream Kraken client returns a NORMALIZED ticker:
                # {'price'|'lastPrice', 'priceChangePercent', 'quoteVolume', ...}
                # — no raw 'c'/'b'/'a' arrays and no bid/ask fields.
                price = float(ticker.get('price') or ticker.get('lastPrice') or 0)
                change_24h_pct = float(ticker.get('priceChangePercent') or 0.0)

                if price <= 0:
                    continue

                # Bid/ask are not provided by the normalized ticker — the
                # spread below is a declared default estimate, not a reading.
                spread_pct = 0.002

                base = display.split('/')[0]
                vol_estimates = {'BTC': 0.025, 'ETH': 0.030, 'SOL': 0.045}
                vol = vol_estimates.get(base, 0.03)

                liq_scores = {'BTC': 0.90, 'ETH': 0.85, 'SOL': 0.70}
                liq = liq_scores.get(base, 0.5)

                ground = HuntingGround(
                    exchange='kraken',
                    symbol=display,
                    price=price,
                    spread_pct=spread_pct,
                    fee_pct=EXCHANGE_FEES['kraken']['crypto'],
                    volatility_1h=vol,
                    liquidity_score=liq
                )
                ground.change_24h_pct = change_24h_pct
                grounds.append(ground)

            except Exception as e:
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
        
        # Filter by minimum score
        viable = [g for g in all_grounds if g.hunt_score >= min_score]
        
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
              f"{'SPREAD':>8} {'RT COST':>8} {'24H CHG':>8} {'VOL*':>6} {'SCORE':>8}")
        print("-" * 88)

        for i, g in enumerate(grounds[:10], 1):
            status = "✅" if g.hunt_score >= 1.5 else "⚠️" if g.hunt_score >= 0.5 else "❌"
            chg = f"{g.change_24h_pct:>+7.2f}%" if g.change_24h_pct is not None else "    n/a"
            print(f"{status} {i:<3} {g.exchange:<10} {g.symbol:<12} ${g.price:>10.2f} "
                  f"{g.spread_pct*100:>7.3f}% {g.round_trip_cost*100:>7.3f}% "
                  f"{chg} {g.volatility_1h*100:>5.1f}% {g.hunt_score:>7.1f}")

        print()
        print("* VOL column is a declared per-asset estimate, not a live measurement.")
        print("=" * 88)

        best = grounds[0]
        print(f"🎯 BEST HUNTING GROUND: {best.exchange.upper()} - {best.symbol}")
        print(f"   Round-trip cost: {best.round_trip_cost*100:.3f}%")
        print(f"   Min profit needed: {best.profit_threshold*100:.3f}%")
        print(f"   Est. hourly volatility: {best.volatility_1h*100:.1f}% (estimate)")
        if best.change_24h_pct is not None:
            print(f"   Real 24h change: {best.change_24h_pct:+.2f}%")
        print(f"   HUNT SCORE: {best.hunt_score:.1f}")
        print("=" * 88)

    def write_state(self, path=None):
        """Journal the scan to a JSON state file for the battle-view/progress feed.

        Fail-closed: venues that produced no grounds are recorded with an
        explicit null/error field rather than silently omitted.
        """
        import json as _json
        from datetime import datetime as _dt

        if path is None:
            path = Path(__file__).resolve().parent.parent / 'state' / 'hunting_grounds.json'

        grounds = self.find_best_grounds(min_score=0)
        alpaca_grounds = [g for g in grounds if g.exchange == 'alpaca']
        kraken_grounds = [g for g in grounds if g.exchange == 'kraken']

        state = {
            'timestamp': _dt.now().isoformat(),
            'best_ground': {
                'exchange': grounds[0].exchange,
                'symbol': grounds[0].symbol,
                'price': grounds[0].price,
                'hunt_score': grounds[0].hunt_score,
                'round_trip_cost_pct': grounds[0].round_trip_cost * 100,
            } if grounds else None,
            'grounds': [
                {
                    'rank': i + 1,
                    'exchange': g.exchange,
                    'symbol': g.symbol,
                    'price': g.price,
                    'spread_pct': g.spread_pct,
                    'spread_is_estimate': g.exchange == 'kraken',  # venue provides no bid/ask in normalized ticker
                    'change_24h_pct': g.change_24h_pct,
                    'round_trip_cost_pct': g.round_trip_cost * 100,
                    'volatility_1h_estimate_pct': g.volatility_1h * 100,
                    'hunt_score': g.hunt_score,
                }
                for i, g in enumerate(grounds[:10])
            ],
            'venues': {
                'alpaca': {'grounds': len(alpaca_grounds)} if self.alpaca
                           else {'grounds': 0, 'error': 'client unavailable'},
                'kraken': {'grounds': len(kraken_grounds)} if self.kraken
                           else {'grounds': 0, 'error': 'client unavailable'},
            },
        }

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_json.dumps(state, indent=2))
        logger.info(f"State written to {path}")
        return path


def main():
    """Run hunting ground analysis."""
    hunter = OrcaHuntingGrounds()
    hunter.print_analysis()
    hunter.write_state()


if __name__ == "__main__":
    main()
