"""
Aureon Capital Momentum Bridge

Wires Aureon animal momentum scanners to Capital.com Honey Ladder.

Reads Capital.com price data, runs LoneWolf/LionHunt/Ant logic,
outputs signals to aureon_bridge_signals.jsonl for the radar to pick up.

Gary Leckey | 2026 | ONE TRADE AT A TIME
"""

import json
import logging
import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── SACRED CONSTANTS ──
PHI = (1 + math.sqrt(5)) / 2  # 1.618
MIN_MOVE_PCT = 0.3  # 0.3% move threshold (tighter than crypto's 1%+)

RADAR_DIR = Path(__file__).parent
SIGNAL_FILE = RADAR_DIR / "aureon_bridge_signals.jsonl"

# Capital.com symbols we trade
CAPITAL_SYMBOLS = {
    # Forex
    "USDJPY": "forex",
    "EURUSD": "forex",
    "GBPUSD": "forex",
    # Tech/Indices
    "US100": "tech",
    "AAPL": "tech",
    "TSLA": "tech",
    "NVDA": "tech",
    # Commodities
    "GOLD": "commodity",
    "SILVER": "commodity",
    "OIL_CRUDE": "commodity",
    "NATURALGAS": "commodity",
    # Crypto
    "BTCUSD": "crypto",
    "ETHUSD": "crypto",
}


@dataclass
class MomentumSignal:
    symbol: str
    direction: str  # LONG or SHORT
    confidence: float  # 0.0-1.0
    source: str  # wolf, lion, ant, hummingbird
    move_pct: float
    coherence: float
    timestamp: str


class CapitalMomentumScanner:
    """
    Momentum scanner using Capital.com price data.
    
    Simulates the Aureon animal scanners but for CFD symbols.
    No Alpaca/Binance dependency - pure Capital.com data.
    """
    
    def __init__(self, capital_connector=None):
        self.price_history: Dict[str, List[float]] = {}  # symbol -> list of recent prices
        self.last_scan_time: float = 0
        self.scan_interval = 60  # seconds between scans
        
        # Try to get Capital connector, else use mock data
        self.capital = capital_connector
        # DON'T seed with mock data - build from real prices
        self.price_history = {}
    
    def _init_mock_history(self):
        """DEPRECATED - build history from real prices instead."""
        pass
    
    def feed_price(self, symbol: str, price: float):
        """Feed a new price into the history."""
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        self.price_history[symbol].append(price)
        # Keep last 48 hours of data (assuming 1 price per hour)
        if len(self.price_history[symbol]) > 48:
            self.price_history[symbol] = self.price_history[symbol][-48:]
    
    def feed_prices_from_capital(self, capital_connector, symbols: list):
        """Fetch prices using the price feed router (Binance/Kraken/Capital)."""
        try:
            from aureon_price_feed import get_all_prices
            prices = get_all_prices(symbols, capital_connector)
            for sym, price in prices.items():
                if price > 0:
                    self.feed_price(sym, price)
        except Exception as e:
            logger.debug(f"Price feed error: {e}")
    
    def calculate_momentum(self, symbol: str) -> Optional[MomentumSignal]:
        """Calculate 24h momentum for a symbol."""
        history = self.price_history.get(symbol, [])
        if len(history) < 6:
            return None
        
        first_price = history[0]
        last_price = history[-1]
        
        if first_price <= 0 or last_price <= 0:
            return None
        
        move_pct = ((last_price - first_price) / first_price) * 100.0
        abs_move = abs(move_pct)
        
        # Minimum threshold
        if abs_move < MIN_MOVE_PCT:
            return None
        
        # Coherence: how stable was the move?
        if len(history) >= 12:
            recent = history[-12:]
            highs = max(recent)
            lows = min(recent)
            var = (highs - lows) / last_price * 100 if last_price > 0 else 1.0
            coherence = 1.0 / (1.0 + var)
        else:
            coherence = 0.5
        
        # Confidence: scale with move size and coherence
        # 0.3% move = ~0.4 confidence, 1.0% move = ~0.8 confidence, 2.0%+ = ~0.95
        base_conf = min(abs_move / 2.0, 0.95)
        confidence = base_conf * (0.5 + 0.5 * coherence)
        confidence = min(confidence, 0.99)
        
        # Direction
        direction = "LONG" if move_pct > 0 else "SHORT"
        
        # Source: wolf for big moves, lion for medium, ant for small
        if abs_move >= 1.0:
            source = "wolf"
        elif abs_move >= 0.6:
            source = "lion"
        else:
            source = "ant"
        
        return MomentumSignal(
            symbol=symbol,
            direction=direction,
            confidence=round(confidence, 2),
            source=source,
            move_pct=round(move_pct, 3),
            coherence=round(coherence, 2),
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    
    def scan_all(self) -> List[MomentumSignal]:
        """Scan all symbols and return momentum signals."""
        signals = []
        
        for symbol in CAPITAL_SYMBOLS:
            sig = self.calculate_momentum(symbol)
            if sig and sig.confidence >= 0.4:
                signals.append(sig)
        
        # Sort by confidence (highest first)
        signals.sort(key=lambda x: -x.confidence)
        return signals
    
    def write_signals(self, signals: List[MomentumSignal]):
        """Write signals to the bridge file for the radar to pick up."""
        with open(SIGNAL_FILE, 'a') as f:
            for sig in signals:
                record = {
                    "symbol": sig.symbol,
                    "direction": sig.direction,
                    "confidence": sig.confidence,
                    "source": f"aureon_{sig.source}",
                    "move_pct": sig.move_pct,
                    "coherence": sig.coherence,
                    "timestamp": sig.timestamp,
                    "sector": CAPITAL_SYMBOLS.get(sig.symbol, "commodity"),
                }
                f.write(json.dumps(record) + '\n')
        
        if signals:
            logger.info(f"[MOMENTUM BRIDGE] Wrote {len(signals)} signals to bridge file")
            for sig in signals[:3]:
                logger.info(f"  {sig.symbol} {sig.direction} conf={sig.confidence:.2f} "
                           f"({sig.source}, move={sig.move_pct:+.3f}%)")


def run_momentum_scan(capital_connector=None):
    """Run one momentum scan and write signals."""
    scanner = CapitalMomentumScanner(capital_connector)
    signals = scanner.scan_all()
    scanner.write_signals(signals)
    return signals


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_momentum_scan()
