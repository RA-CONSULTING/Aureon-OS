"""
🦙📈 AUREON ALPACA STOCK SCANNER 📈🦙

Dedicated stock scanner for US equities on Alpaca platform.
Scans for momentum, volume breakouts, and technical patterns.

Unlike crypto arbitrage, stock scanning focuses on:
- Price momentum (20/50/200 MA crossovers)
- Volume spikes (unusual activity)
- Volatility patterns (Bollinger Bands, ATR)
- Gap analysis (pre-market/post-market momentum)
- Sector rotation signals

Gary Leckey | January 2026 | STOCK MOMENTUM MODE
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
import os
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
        # Skip stderr wrapping (causes Windows exit errors)
    except Exception:
        pass

import logging
import time
import math
from typing import Dict, List, Optional, Tuple
from dataclasses import asdict, dataclass, field
from collections import deque

# 🚌 Communication Buses
try:
    from aureon.core.aureon_thought_bus import ThoughtBus, Thought
    THOUGHT_BUS_AVAILABLE = True
except ImportError:
    THOUGHT_BUS_AVAILABLE = False
    ThoughtBus = None

try:
    from aureon.core.aureon_chirp_bus import ChirpBus
    CHIRP_BUS_AVAILABLE = True
except ImportError:
    CHIRP_BUS_AVAILABLE = False
    ChirpBus = None

logger = logging.getLogger(__name__)

PHI = (1 + math.sqrt(5)) / 2  # Golden ratio
LOVE_FREQUENCY = 528  # Hz DNA repair frequency

# Stock trading fees and costs
STOCK_BROKER_FEE_PCT = 0.0  # Alpaca = commission-free
STOCK_BID_ASK_SPREAD_EST_PCT = 0.01  # 1 bps typical for liquid stocks
STOCK_SLIPPAGE_EST_PCT = 0.01  # 1 bps for execution slippage
STOCK_ROUND_TRIP_COST_PCT = STOCK_BROKER_FEE_PCT + STOCK_BID_ASK_SPREAD_EST_PCT + STOCK_SLIPPAGE_EST_PCT  # ~0.02%


@dataclass
class StockOpportunity:
    """Stock trading opportunity with momentum scoring."""
    symbol: str
    price: float
    bid: float
    ask: float
    spread_pct: float
    change_24h: float
    volume: float
    momentum_score: float
    volume_score: float
    volatility_score: float
    combined_score: float
    timestamp: float
    signal_type: str = "MOMENTUM"  # MOMENTUM, BREAKOUT, REVERSAL, GAP
    confidence: float = 0.0
    expected_move_pct: float = 0.0
    expected_net_move_pct: float = 0.0
    broker_fee_pct: float = 0.0
    round_trip_cost_pct: float = 0.0
    expected_net_profit_pct: float = 0.0
    passes_profit_gate: bool = False
    reasoning: str = ""


class AlpacaStockScanner:
    """
    🦙📈 Dedicated stock scanner for Alpaca US equities.
    
    Scans for:
    - Momentum patterns (MA crossovers)
    - Volume breakouts (unusual activity)
    - Volatility expansion (potential big moves)
    - Technical patterns (gaps, flags, triangles)
    """
    
    def __init__(self, alpaca_client=None):
        self.alpaca = alpaca_client
        self.price_history: Dict[str, deque] = {}  # Rolling price history
        self.volume_history: Dict[str, deque] = {}  # Rolling volume history
        self.history_window = 50  # Keep 50 data points for MA calculations
        
        # Bus Integration
        self.thought_bus = ThoughtBus() if THOUGHT_BUS_AVAILABLE else None
        self.chirp_bus = None
        if CHIRP_BUS_AVAILABLE:
            try:
                self.chirp_bus = ChirpBus()
            except Exception:
                pass
        
    def scan_stocks(
        self,
        symbols: Optional[List[str]] = None,
        max_results: int = 50,
        min_volume: float = 1000000.0,  # $1M minimum daily volume
        min_price: float = 1.0,  # $1 minimum price
        max_price: float = 1000.0  # $1000 maximum price
    ) -> List[StockOpportunity]:
        """
        Scan stocks for trading opportunities.

        ⚠️ WARNING: This uses Alpaca API and may hit 404/429 on some accounts.
        Prefer Kraken/Binance for data (heavy lifting) and use Alpaca only for execution.

        Args:
            symbols: List of stock symbols to scan (None = all tradable)
            max_results: Maximum opportunities to return
            min_volume: Minimum daily volume in USD
            min_price: Minimum stock price
            max_price: Maximum stock price
            
        Returns:
            List of stock opportunities ranked by combined score
        """
        if not self.alpaca:
            logger.warning("No Alpaca client available for stock scanning")
            return []
        
        # Get symbols to scan
        if symbols is None:
            try:
                if hasattr(self.alpaca, 'get_tradable_stock_symbols'):
                    symbols = self.alpaca.get_tradable_stock_symbols() or []
                else:
                    logger.warning("Alpaca client missing get_tradable_stock_symbols()")
                    return []
            except Exception as e:
                logger.error(f"Failed to get stock symbols: {e}")
                return []
        
        if not symbols:
            return []
        
        # Limit to reasonable batch size using volume filter
        if len(symbols) > 500:
            symbols = self._filter_to_top_volume_stocks(symbols, limit=500)
        
        opportunities = []
        timestamp = time.time()
        
        # Fetch latest quotes in batches
        batch_size = 100
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            
            try:
                # Get latest stock quotes
                quotes = self._fetch_stock_quotes(batch)
                
                for symbol, quote in quotes.items():
                    price = quote.get('price', 0)
                    volume = quote.get('volume', 0)
                    change_pct = quote.get('change_pct', 0)
                    
                    # Apply filters
                    if price < min_price or price > max_price:
                        continue
                    if volume * price < min_volume:
                        continue
                    
                    # Update history
                    self._update_history(symbol, price, volume)
                    
                    # Calculate scores
                    momentum_score = self._calculate_momentum_score(symbol, price, change_pct)
                    volume_score = self._calculate_volume_score(symbol, volume)
                    volatility_score = self._calculate_volatility_score(symbol, price)
                    
                    # Combined score (weighted average)
                    combined_score = (
                        momentum_score * 0.4 +
                        volume_score * 0.3 +
                        volatility_score * 0.3
                    )
                    
                    # Signal classification
                    signal_type = self._classify_signal(momentum_score, volume_score, volatility_score)
                    
                    # Confidence based on score alignment
                    confidence = self._calculate_confidence(momentum_score, volume_score, volatility_score)
                    
                    # Expected move (simple heuristic) and cost/slippage
                    expected_move_pct = abs(change_pct) * (1 + volatility_score)
                    spread_pct = quote.get('spread_pct', 0.0)
                    cost_buffer_pct = 0.02  # 2 bps for fees/latency safety
                    expected_net_move_pct = expected_move_pct - spread_pct - cost_buffer_pct
                    
                    # Profit gate: ensure minimum positive profit after all costs
                    round_trip_cost = STOCK_ROUND_TRIP_COST_PCT * 100  # Convert to bps
                    expected_net_profit_pct = expected_net_move_pct - round_trip_cost
                    passes_profit_gate = expected_net_profit_pct > 0.05  # Min 0.5 bps net profit
                    
                    # Generate reasoning
                    reasoning = self._generate_reasoning(
                        symbol, signal_type, momentum_score, volume_score, volatility_score
                    )
                    
                    if combined_score > 0.5 and passes_profit_gate:  # Minimum threshold + profit gate

                        opportunities.append(StockOpportunity(
                            symbol=symbol,
                            price=price,
                            bid=quote.get('bid', 0.0),
                            ask=quote.get('ask', 0.0),
                            spread_pct=spread_pct,
                            change_24h=change_pct,
                            volume=volume,
                            momentum_score=momentum_score,
                            volume_score=volume_score,
                            volatility_score=volatility_score,
                            combined_score=combined_score,
                            timestamp=timestamp,
                            signal_type=signal_type,
                            confidence=confidence,
                            expected_move_pct=expected_move_pct,
                            expected_net_move_pct=expected_net_move_pct,
                            broker_fee_pct=STOCK_BROKER_FEE_PCT,
                            round_trip_cost_pct=STOCK_ROUND_TRIP_COST_PCT,
                            expected_net_profit_pct=expected_net_profit_pct,
                            passes_profit_gate=passes_profit_gate,
                            reasoning=reasoning
                        ))
            
            except Exception as e:
                logger.warning(f"Error scanning stock batch: {e}")
                continue
        
        # Sort by combined score (highest first)
        opportunities.sort(key=lambda x: x.combined_score, reverse=True)
        
        # Publish best opportunities
        results = opportunities[:max_results]
        for opp in results[:3]:
            self._publish_opportunity(opp)
            
        return results
    
    def _publish_opportunity(self, opp: StockOpportunity) -> None:
        """Publish opportunity to ThoughtBus and ChirpBus."""
        try:
            # 1. ThoughtBus
            if self.thought_bus:
                self.thought_bus.publish(Thought(
                    source="ALPACA_STOCK_SCANNER",
                    thought_type="STOCK_OPPORTUNITY",
                    priority=2,
                    content=asdict(opp)
                ))

            # 2. ChirpBus
            if self.chirp_bus:
                self.chirp_bus.publish("stock.opportunity", {
                    "sym": opp.symbol,
                    "score": opp.combined_score,
                    "signal": opp.signal_type,
                    "conf": opp.confidence
                })
        except Exception as e:
            logger.error(f"Failed to publish stock opportunity: {e}")

    def _filter_to_top_volume_stocks(self, symbols: List[str], limit: int = 500) -> List[str]:
        """Filter to highest volume stocks using BULK snapshots (Heavy Lifting)."""
        if not self.alpaca:
            return symbols[:limit]

        # Process a larger subset since we can now fetch efficiently
        subset = symbols[:2000]
        volumes: List[Tuple[str, float]] = []

        try:
            # Use new bulk snapshot method
            if hasattr(self.alpaca, 'get_stock_snapshots'):
                snapshots = self.alpaca.get_stock_snapshots(subset)
                for sym, snap in snapshots.items():
                    if not snap: continue
                    # Handle both camelCase (API) and snake_case (Client) keys
                    daily = snap.get('dailyBar', {}) or snap.get('daily_bar', {})
                    vol = float(daily.get('v', 0) or 0.0)
                    if vol > 0:
                        volumes.append((sym, vol))
            else:
                # Fallback if method missing (shouldn't happen with patch)
                logger.warning("Alpaca client missing get_stock_snapshots, using slow filter")
                return symbols[:limit]
                
        except Exception as e:
            logger.error(f"Error in heavy lifting volume filter: {e}")
            return symbols[:limit]

        if not volumes:
            return symbols[:limit]

        volumes.sort(key=lambda x: x[1], reverse=True)
        return [sym for sym, _ in volumes[:limit]]
    
    def _fetch_stock_quotes(self, symbols: List[str]) -> Dict[str, Dict]:
        """Fetch latest quotes using BULK snapshots (Heavy Lifting Optimized)."""
        quotes = {}
        
        try:
            # Use bulk fetch instead of iterative loop
            if hasattr(self.alpaca, 'get_stock_snapshots'):
                snapshots = self.alpaca.get_stock_snapshots(symbols)
                
                for sym, snap in snapshots.items():
                    if not snap: continue
                    
                    # Extract Data
                    latest_trade = snap.get('latestTrade', {}) or snap.get('latest_trade', {})
                    latest_quote = snap.get('latestQuote', {}) or snap.get('latest_quote', {})
                    daily_bar = snap.get('dailyBar', {}) or snap.get('daily_bar', {})
                    
                    price = float(latest_trade.get('p', 0) or 0)
                    bid = float(latest_quote.get('bp', 0) or 0)
                    ask = float(latest_quote.get('ap', 0) or 0)
                    volume = float(daily_bar.get('v', 0) or 0)
                    open_price = float(daily_bar.get('o', 0) or 0)
                    
                    # Calculate Stats
                    spread_pct = 0.0
                    if bid > 0 and ask > 0:
                        mid = (bid + ask) / 2
                        spread_pct = ((ask - bid) / mid) * 100
                    
                    change_pct = 0.0
                    if open_price > 0 and price > 0:
                        change_pct = ((price - open_price) / open_price) * 100
                    
                    if price > 0:
                        quotes[sym] = {
                            'price': price,
                            'bid': bid,
                            'ask': ask,
                            'spread_pct': spread_pct,
                            'volume': volume,
                            'change_pct': change_pct
                        }
            else:
                logger.warning("Alpaca client missing get_stock_snapshots")
                
        except Exception as e:
            logger.error(f"Failed to fetch stock quotes batch: {e}")
        
        return quotes
    
    def _update_history(self, symbol: str, price: float, volume: float):
        """Update rolling price and volume history."""
        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=self.history_window)
        if symbol not in self.volume_history:
            self.volume_history[symbol] = deque(maxlen=self.history_window)
        
        self.price_history[symbol].append(price)
        self.volume_history[symbol].append(volume)
    
    def _calculate_momentum_score(self, symbol: str, price: float, change_pct: float) -> float:
        """
        Calculate momentum score based on price action.
        
        - Recent price change
        - Moving average position
        - Trend strength
        """
        score = 0.5  # Neutral baseline
        
        # Recent change component (±50%)
        if change_pct > 0:
            score += min(change_pct / 10, 0.25)  # Cap at +25%
        else:
            score += max(change_pct / 10, -0.25)  # Cap at -25%
        
        # Moving average component (if history available)
        if symbol in self.price_history and len(self.price_history[symbol]) >= 20:
            prices = list(self.price_history[symbol])
            ma20 = sum(prices[-20:]) / 20
            
            # Price above MA20 = bullish
            if price > ma20:
                distance = (price - ma20) / ma20
                score += min(distance * 0.5, 0.25)  # Up to +25%
            else:
                distance = (ma20 - price) / ma20
                score -= min(distance * 0.5, 0.25)  # Up to -25%
        
        return max(0.0, min(1.0, score))
    
    def _calculate_volume_score(self, symbol: str, volume: float) -> float:
        """
        Calculate volume score based on unusual activity.
        
        - Volume relative to average
        - Volume trend
        """
        score = 0.5  # Neutral baseline
        
        if symbol in self.volume_history and len(self.volume_history[symbol]) >= 20:
            volumes = list(self.volume_history[symbol])
            avg_volume = sum(volumes[-20:]) / 20
            
            if avg_volume > 0:
                volume_ratio = volume / avg_volume
                
                # Higher than average = more activity
                if volume_ratio > 1.0:
                    score += min((volume_ratio - 1.0) * 0.25, 0.5)  # Up to +50%
                else:
                    score -= min((1.0 - volume_ratio) * 0.25, 0.3)  # Down to -30%
        
        return max(0.0, min(1.0, score))
    
    def _calculate_volatility_score(self, symbol: str, price: float) -> float:
        """
        Calculate volatility score based on price movement.
        
        - Price range over history
        - Recent volatility
        """
        score = 0.5  # Neutral baseline
        
        if symbol in self.price_history and len(self.price_history[symbol]) >= 20:
            prices = list(self.price_history[symbol])
            
            # Calculate recent price range
            recent_high = max(prices[-20:])
            recent_low = min(prices[-20:])
            recent_avg = sum(prices[-20:]) / 20
            
            if recent_avg > 0:
                price_range_pct = (recent_high - recent_low) / recent_avg
                
                # Higher volatility = higher score (more opportunity)
                score += min(price_range_pct * 0.5, 0.5)  # Up to +50%
        
        return max(0.0, min(1.0, score))
    
    def _classify_signal(
        self,
        momentum_score: float,
        volume_score: float,
        volatility_score: float
    ) -> str:
        """Classify the signal type based on score characteristics."""
        if momentum_score > 0.7 and volume_score > 0.7:
            return "BREAKOUT"
        elif momentum_score > 0.6:
            return "MOMENTUM"
        elif volatility_score > 0.7:
            return "VOLATILITY"
        elif momentum_score < 0.4 and volume_score > 0.6:
            return "REVERSAL"
        else:
            return "NEUTRAL"
    
    def _calculate_confidence(
        self,
        momentum_score: float,
        volume_score: float,
        volatility_score: float
    ) -> float:
        """Calculate confidence based on score alignment."""
        # High confidence when all scores agree (all high or all low)
        scores = [momentum_score, volume_score, volatility_score]
        avg_score = sum(scores) / len(scores)
        variance = sum((s - avg_score) ** 2 for s in scores) / len(scores)
        
        # Low variance = high alignment = high confidence
        confidence = 1.0 - min(variance * 2, 0.5)  # Scale variance to confidence
        
        # Boost confidence if scores are extreme
        if avg_score > 0.7 or avg_score < 0.3:
            confidence += 0.1
        
        return max(0.0, min(1.0, confidence))
    
    def _generate_reasoning(
        self,
        symbol: str,
        signal_type: str,
        momentum_score: float,
        volume_score: float,
        volatility_score: float
    ) -> str:
        """Generate human-readable reasoning for the signal."""
        parts = []
        
        if signal_type == "BREAKOUT":
            parts.append("Strong momentum + high volume = breakout")
        elif signal_type == "MOMENTUM":
            parts.append("Positive momentum trend")
        elif signal_type == "REVERSAL":
            parts.append("Volume spike with weak momentum = potential reversal")
        elif signal_type == "VOLATILITY":
            parts.append("High volatility = large move opportunity")
        
        if momentum_score > 0.6:
            parts.append(f"momentum={momentum_score:.2f}")
        if volume_score > 0.6:
            parts.append(f"volume={volume_score:.2f}")
        if volatility_score > 0.6:
            parts.append(f"volatility={volatility_score:.2f}")
        
        return ", ".join(parts) if parts else "Neutral signal"


def test_stock_scanner():
    """Test the stock scanner with sample data."""
    print("🦙📈 Testing Alpaca Stock Scanner...")
    
    from aureon.exchanges.alpaca_client import AlpacaClient
    
    alpaca = AlpacaClient()
    scanner = AlpacaStockScanner(alpaca_client=alpaca)
    
    # Test with popular stocks
    test_symbols = ["AAPL", "MSFT", "NVDA", "TSLA", "GOOGL", "META", "AMZN"]
    
    opportunities = scanner.scan_stocks(
        symbols=test_symbols,
        max_results=10,
        min_volume=100000,  # Lower for testing
        min_price=0.5
    )
    
    print(f"\n📊 Found {len(opportunities)} stock opportunities:")
    for i, opp in enumerate(opportunities[:5], 1):
        print(f"\n{i}. {opp.symbol} @ ${opp.price:.2f}")
        print(f"   Signal: {opp.signal_type}")
        print(f"   Combined Score: {opp.combined_score:.3f}")
        print(f"   Confidence: {opp.confidence:.2f}")
        print(f"   Change 24h: {opp.change_24h:.2f}%")
        print(f"   Expected Move: {opp.expected_move_pct:.2f}%")
        print(f"   Reasoning: {opp.reasoning}")


if __name__ == "__main__":
    test_stock_scanner()
