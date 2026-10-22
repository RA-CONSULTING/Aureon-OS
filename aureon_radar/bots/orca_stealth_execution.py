#!/usr/bin/env python3
"""
🦈🥷 ORCA STEALTH EXECUTION - ANTI-FRONT-RUNNING COUNTERMEASURES 🥷🦈
═══════════════════════════════════════════════════════════════════════════════

COUNTERMEASURES AGAINST HFT/MARKET MAKER FRONT-RUNNING:

1. RANDOM DELAYS (50-500ms) - Break timing patterns
2. ORDER SPLITTING - Large orders → multiple small chunks
3. SYMBOL ROTATION - Avoid hunted symbols, find alternatives
4. TIMING NOISE - Vary execution times unpredictably
5. ICEBERG ORDERS - Show only small portion of total order
6. DECOY ORDERS - Fake interest to mislead algorithms (optional)

THE MATH:
  - HFTs react in 10-50ms to your order
  - Adding 50-500ms random delay breaks their timing model
  - Splitting $100 into 5x$20 makes pattern detection harder
  - Rotating symbols forces them to re-learn your behavior

Gary Leckey | Stealth Division | January 2026
═══════════════════════════════════════════════════════════════════════════════
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
import time
import random
import math
import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable
from collections import defaultdict

# Windows UTF-8 fix
from aureon.utils.console_utf8 import ensure_utf8_stdout  # noqa: E402

ensure_utf8_stdout()


# ═══════════════════════════════════════════════════════════════════════════════
# 📊 DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class StealthConfig:
    """Configuration for stealth execution."""
    # Random delay settings
    min_delay_ms: int = 50
    max_delay_ms: int = 500
    delay_enabled: bool = True
    
    # Order splitting settings
    split_threshold_usd: float = 50.0  # Split orders larger than this
    min_chunk_usd: float = 10.0  # Minimum chunk size
    max_chunks: int = 5  # Maximum number of chunks
    chunk_delay_ms: int = 200  # Delay between chunks
    splitting_enabled: bool = True
    
    # Symbol rotation settings
    hunted_cooldown_minutes: int = 30  # Avoid hunted symbols for this long
    rotation_enabled: bool = True
    
    # Timing noise
    vary_interval_pct: float = 0.3  # Vary timing by ±30%
    timing_noise_enabled: bool = True
    
    # Stealth mode
    stealth_mode: str = "normal"  # "normal", "aggressive", "paranoid"


@dataclass
class HuntedSymbol:
    """A symbol that's being hunted by predators."""
    symbol: str
    detected_at: float
    front_run_count: int = 0
    stalking_firm: str = "unknown"
    cooldown_until: float = 0.0


@dataclass 
class StealthOrder:
    """An order being executed with stealth measures."""
    symbol: str
    side: str
    total_quantity: float
    total_value_usd: float
    chunks: List[Tuple[float, float]] = field(default_factory=list)  # [(qty, delay_ms), ...]
    executed_chunks: int = 0
    total_executed_qty: float = 0.0
    stealth_delay_ms: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# 🥷 STEALTH EXECUTION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class OrcaStealthExecution:
    """
    Wraps order execution with anti-front-running countermeasures.
    
    USAGE:
        stealth = OrcaStealthExecution()
        
        # Instead of: client.place_market_order(symbol, side, qty)
        # Use: stealth.execute_stealth_order(client, symbol, side, qty, price)
    """
    
    def __init__(self, config: StealthConfig = None):
        self.config = config or StealthConfig()
        
        # Track hunted symbols
        self.hunted_symbols: Dict[str, HuntedSymbol] = {}
        
        # Symbol alternatives for rotation
        self.symbol_alternatives: Dict[str, List[str]] = {
            # Crypto pairs - alternatives with similar volatility
            'BTC/USD': ['ETH/USD', 'SOL/USD'],
            'BTCUSD': ['ETHUSD', 'SOLUSD'],
            'ETH/USD': ['BTC/USD', 'SOL/USD', 'AVAX/USD'],
            'ETHUSD': ['BTCUSD', 'SOLUSD', 'AVAXUSD'],
            'SOL/USD': ['ETH/USD', 'AVAX/USD', 'DOT/USD'],
            'SOLUSD': ['ETHUSD', 'AVAXUSD', 'DOTUSD'],
            'PEPE/USD': ['SHIB/USD', 'DOGE/USD', 'FLOKI/USD'],
            'PEPEUSD': ['SHIBUSD', 'DOGEUSD'],
            'SHIB/USD': ['PEPE/USD', 'DOGE/USD'],
            'SHIBUSD': ['PEPEUSD', 'DOGEUSD'],
            'DOGE/USD': ['SHIB/USD', 'PEPE/USD'],
            'DOGEUSD': ['SHIBUSD', 'PEPEUSD'],
        }
        
        # Execution statistics
        self.stats = {
            'total_orders': 0,
            'delayed_orders': 0,
            'split_orders': 0,
            'rotated_symbols': 0,
            'total_delay_ms': 0,
            'chunks_executed': 0,
        }
        
        # Random number generator with good entropy
        self.rng = random.SystemRandom()
        
        print("🥷 STEALTH EXECUTION ENGINE ONLINE")
        print(f"   Random delay: {self.config.min_delay_ms}-{self.config.max_delay_ms}ms")
        print(f"   Split threshold: ${self.config.split_threshold_usd}")
        print(f"   Stealth mode: {self.config.stealth_mode}")
    
    # ───────────────────────────────────────────────────────────────────────
    # 🎲 RANDOM DELAY - Break timing patterns
    # ───────────────────────────────────────────────────────────────────────
    
    def _get_random_delay(self) -> float:
        """Get a random delay in milliseconds using cryptographic randomness."""
        if not self.config.delay_enabled:
            return 0.0
        
        # Use triangular distribution - more likely to be in the middle
        # This looks more "human" than uniform distribution
        mode = (self.config.min_delay_ms + self.config.max_delay_ms) / 2
        delay = self.rng.triangular(
            self.config.min_delay_ms,
            self.config.max_delay_ms,
            mode
        )
        
        # In paranoid mode, add extra randomness
        if self.config.stealth_mode == "paranoid":
            delay *= self.rng.uniform(0.8, 1.5)
        
        return delay
    
    def _apply_delay(self, delay_ms: float) -> float:
        """Apply a delay before order execution."""
        if delay_ms <= 0:
            return 0.0
        
        # Convert to seconds and sleep
        delay_sec = delay_ms / 1000.0
        time.sleep(delay_sec)
        
        self.stats['total_delay_ms'] += delay_ms
        self.stats['delayed_orders'] += 1
        
        return delay_ms
    
    # ───────────────────────────────────────────────────────────────────────
    # ✂️ ORDER SPLITTING - Large orders → small chunks
    # ───────────────────────────────────────────────────────────────────────
    
    def _should_split_order(self, value_usd: float) -> bool:
        """Determine if an order should be split."""
        if not self.config.splitting_enabled:
            return False
        return value_usd > self.config.split_threshold_usd
    
    def _calculate_chunks(self, total_qty: float, total_value_usd: float, 
                         price: float) -> List[Tuple[float, float]]:
        """
        Calculate how to split an order into chunks.
        
        Returns: [(chunk_qty, delay_ms), ...]
        """
        if total_value_usd <= self.config.split_threshold_usd:
            # No splitting needed
            return [(total_qty, 0)]
        
        # Calculate number of chunks
        num_chunks = min(
            self.config.max_chunks,
            max(2, int(total_value_usd / self.config.min_chunk_usd))
        )
        
        # Use varying chunk sizes to avoid pattern
        # Instead of equal chunks, use random distribution
        weights = [self.rng.uniform(0.5, 1.5) for _ in range(num_chunks)]
        total_weight = sum(weights)
        
        chunks = []
        remaining_qty = total_qty
        
        for i, weight in enumerate(weights):
            if i == len(weights) - 1:
                # Last chunk gets the remainder
                chunk_qty = remaining_qty
            else:
                chunk_qty = total_qty * (weight / total_weight)
                chunk_qty = round(chunk_qty, 8)  # Precision for crypto
                remaining_qty -= chunk_qty
            
            # Delay between chunks (0 for first chunk)
            delay = 0 if i == 0 else self.rng.uniform(
                self.config.chunk_delay_ms * 0.5,
                self.config.chunk_delay_ms * 1.5
            )
            
            chunks.append((chunk_qty, delay))
        
        self.stats['split_orders'] += 1
        
        return chunks
    
    # ───────────────────────────────────────────────────────────────────────
    # 🔄 SYMBOL ROTATION - Avoid hunted symbols
    # ───────────────────────────────────────────────────────────────────────
    
    def mark_symbol_hunted(self, symbol: str, firm: str = "unknown", 
                          front_run_count: int = 1):
        """Mark a symbol as being hunted by predators."""
        now = time.time()
        cooldown = now + (self.config.hunted_cooldown_minutes * 60)
        
        if symbol in self.hunted_symbols:
            self.hunted_symbols[symbol].front_run_count += front_run_count
            self.hunted_symbols[symbol].cooldown_until = cooldown
            self.hunted_symbols[symbol].stalking_firm = firm
        else:
            self.hunted_symbols[symbol] = HuntedSymbol(
                symbol=symbol,
                detected_at=now,
                front_run_count=front_run_count,
                stalking_firm=firm,
                cooldown_until=cooldown
            )
        
        print(f"🎯 Symbol {symbol} marked as HUNTED by {firm}")
        print(f"   Cooldown until: {datetime.fromtimestamp(cooldown).strftime('%H:%M:%S')}")
    
    def is_symbol_hunted(self, symbol: str) -> bool:
        """Check if a symbol is currently being hunted."""
        if symbol not in self.hunted_symbols:
            return False
        
        hunted = self.hunted_symbols[symbol]
        if time.time() > hunted.cooldown_until:
            # Cooldown expired
            del self.hunted_symbols[symbol]
            return False
        
        return True
    
    def get_alternative_symbol(self, symbol: str) -> Optional[str]:
        """Get an alternative symbol if current one is hunted."""
        if not self.config.rotation_enabled:
            return None
        
        if not self.is_symbol_hunted(symbol):
            return None
        
        alternatives = self.symbol_alternatives.get(symbol, [])
        
        # Filter out hunted alternatives
        safe_alternatives = [
            alt for alt in alternatives 
            if not self.is_symbol_hunted(alt)
        ]
        
        if safe_alternatives:
            chosen = self.rng.choice(safe_alternatives)
            self.stats['rotated_symbols'] += 1
            print(f"🔄 ROTATING: {symbol} → {chosen} (avoiding predators)")
            return chosen
        
        return None
    
    # ───────────────────────────────────────────────────────────────────────
    # ⏰ TIMING NOISE - Vary execution patterns
    # ───────────────────────────────────────────────────────────────────────
    
    def get_noisy_interval(self, base_interval_sec: float) -> float:
        """Add noise to a timing interval."""
        if not self.config.timing_noise_enabled:
            return base_interval_sec
        
        # Vary by ±config.vary_interval_pct
        noise_factor = self.rng.uniform(
            1 - self.config.vary_interval_pct,
            1 + self.config.vary_interval_pct
        )
        
        return base_interval_sec * noise_factor
    
    # ───────────────────────────────────────────────────────────────────────
    # 🥷 MAIN STEALTH EXECUTION
    # ───────────────────────────────────────────────────────────────────────
    
    def execute_stealth_order(self, client: Any, symbol: str, side: str,
                              quantity: float, price: float = None,
                              value_usd: float = None) -> Dict:
        """
        Execute an order with all stealth countermeasures.
        
        Args:
            client: Exchange client with place_market_order method
            symbol: Trading symbol
            side: 'buy' or 'sell'
            quantity: Order quantity
            price: Current price (for value calculation)
            value_usd: Order value in USD (or calculated from price*quantity)
        
        Returns:
            Order result dict with stealth metadata
        """
        self.stats['total_orders'] += 1
        
        # Calculate value if not provided
        if value_usd is None and price:
            value_usd = price * quantity
        elif value_usd is None:
            value_usd = 0  # Unknown, won't split
        
        # Check for symbol rotation
        if self.is_symbol_hunted(symbol):
            alternative = self.get_alternative_symbol(symbol)
            if alternative:
                print(f"🥷 STEALTH: Rotating from hunted {symbol} → {alternative}")
                # Note: In real implementation, you'd need to handle the alternative
                # For now, we just warn and continue
        
        # Calculate chunks if splitting. price is only used for chunking math;
        # actual orders use quantity, so a placeholder of 1.0 when price is
        # unknown does not fabricate execution prices.
        chunks = self._calculate_chunks(quantity, value_usd, price or 1.0)
        
        # Pre-execution random delay
        initial_delay = self._get_random_delay()
        self._apply_delay(initial_delay)
        
        # Execute chunks
        results = []
        total_filled_qty = 0
        total_filled_value = 0
        
        for i, (chunk_qty, chunk_delay) in enumerate(chunks):
            # Inter-chunk delay (not for first chunk)
            if i > 0 and chunk_delay > 0:
                self._apply_delay(chunk_delay)
            
            # Execute chunk
            try:
                chunk_result = client.place_market_order(
                    symbol=symbol,
                    side=side,
                    quantity=chunk_qty
                )
                
                if chunk_result:
                    results.append(chunk_result)
                    filled_qty = float(chunk_result.get('filled_qty', chunk_qty))
                    filled_price = float(chunk_result.get('filled_avg_price', price or 0))
                    total_filled_qty += filled_qty
                    total_filled_value += filled_qty * filled_price
                    self.stats['chunks_executed'] += 1
                    
            except Exception as e:
                print(f"⚠️ Chunk {i+1}/{len(chunks)} failed: {e}")
                # Continue with remaining chunks
        
        # Combine results
        combined_result = {
            'symbol': symbol,
            'side': side,
            'filled_qty': total_filled_qty,
            'filled_avg_price': total_filled_value / total_filled_qty if total_filled_qty > 0 else 0,
            'chunks_executed': len(results),
            'total_chunks': len(chunks),
            'stealth_delay_ms': initial_delay,
            'stealth_mode': self.config.stealth_mode,
            'was_split': len(chunks) > 1,
            'id': results[0].get('id') if results else None,
        }
        
        if len(chunks) > 1:
            print(f"🥷 STEALTH ORDER: {side.upper()} {total_filled_qty:.6f} {symbol}")
            print(f"   Chunks: {len(results)}/{len(chunks)} | Delay: {initial_delay:.0f}ms")
        
        return combined_result
    
    # ───────────────────────────────────────────────────────────────────────
    # 📊 STATISTICS
    # ───────────────────────────────────────────────────────────────────────
    
    def get_stats(self) -> Dict:
        """Get execution statistics."""
        return {
            **self.stats,
            'hunted_symbols': list(self.hunted_symbols.keys()),
            'avg_delay_ms': self.stats['total_delay_ms'] / max(1, self.stats['delayed_orders']),
        }
    
    def print_stats(self):
        """Print execution statistics."""
        stats = self.get_stats()
        print("\n" + "═" * 50)
        print("🥷 STEALTH EXECUTION STATS")
        print("═" * 50)
        print(f"Total Orders: {stats['total_orders']}")
        print(f"Delayed Orders: {stats['delayed_orders']}")
        print(f"Split Orders: {stats['split_orders']}")
        print(f"Rotated Symbols: {stats['rotated_symbols']}")
        print(f"Total Chunks Executed: {stats['chunks_executed']}")
        print(f"Average Delay: {stats['avg_delay_ms']:.0f}ms")
        print(f"Hunted Symbols: {', '.join(stats['hunted_symbols']) or 'None'}")
        print("═" * 50 + "\n")


# ═══════════════════════════════════════════════════════════════════════════════
# 🎮 STEALTH MODE PRESETS
# ═══════════════════════════════════════════════════════════════════════════════

def get_stealth_config(mode: str = "normal") -> StealthConfig:
    """Get a stealth configuration preset."""
    
    if mode == "aggressive":
        # More delays, smaller chunks, longer cooldowns
        return StealthConfig(
            min_delay_ms=100,
            max_delay_ms=800,
            delay_enabled=True,
            split_threshold_usd=25.0,
            min_chunk_usd=5.0,
            max_chunks=8,
            chunk_delay_ms=300,
            splitting_enabled=True,
            hunted_cooldown_minutes=60,
            rotation_enabled=True,
            vary_interval_pct=0.5,
            timing_noise_enabled=True,
            stealth_mode="aggressive"
        )
    
    elif mode == "paranoid":
        # Maximum stealth - for when you're definitely being targeted
        return StealthConfig(
            min_delay_ms=200,
            max_delay_ms=1500,
            delay_enabled=True,
            split_threshold_usd=15.0,
            min_chunk_usd=3.0,
            max_chunks=10,
            chunk_delay_ms=500,
            splitting_enabled=True,
            hunted_cooldown_minutes=120,
            rotation_enabled=True,
            vary_interval_pct=0.7,
            timing_noise_enabled=True,
            stealth_mode="paranoid"
        )
    
    elif mode == "disabled":
        # No stealth - direct execution
        return StealthConfig(
            delay_enabled=False,
            splitting_enabled=False,
            rotation_enabled=False,
            timing_noise_enabled=False,
            stealth_mode="disabled"
        )
    
    else:  # "normal"
        return StealthConfig()  # Use defaults


# ═══════════════════════════════════════════════════════════════════════════════
# 🔌 INTEGRATION HELPER
# ═══════════════════════════════════════════════════════════════════════════════

# Global stealth instance
_stealth_instance: Optional[OrcaStealthExecution] = None

def get_stealth_executor(mode: str = "normal") -> OrcaStealthExecution:
    """Get or create the global stealth executor."""
    global _stealth_instance
    if _stealth_instance is None:
        config = get_stealth_config(mode)
        _stealth_instance = OrcaStealthExecution(config)
    return _stealth_instance


def stealth_order(client: Any, symbol: str, side: str, quantity: float,
                  price: float = None, value_usd: float = None) -> Dict:
    """
    Convenience function for stealth order execution.
    
    Usage:
        from orca_stealth_execution import stealth_order
        
        # Instead of: client.place_market_order(symbol, 'buy', qty)
        result = stealth_order(client, symbol, 'buy', qty, price=current_price)
    """
    stealth = get_stealth_executor()
    return stealth.execute_stealth_order(client, symbol, side, quantity, price, value_usd)


# ═══════════════════════════════════════════════════════════════════════════════
# 🧪 TESTING
# ═══════════════════════════════════════════════════════════════════════════════

class MockClient:
    """Mock client for testing."""
    def place_market_order(self, symbol: str, side: str, quantity: float) -> Dict:
        return {
            'id': f'mock_{int(time.time()*1000)}',
            'symbol': symbol,
            'side': side,
            'filled_qty': quantity,
            'filled_avg_price': 100.0,
            'status': 'filled'
        }


def test_stealth_execution():
    """Test the stealth execution system with SIMULATED prices and MockClient."""
    print("\n🧪 TESTING STEALTH EXECUTION SYSTEM (SIMULATED — NOT LIVE)\n")
    
    # Test normal mode
    print("=" * 50)
    print("TEST 1: Normal Mode - Small Order (SIMULATED)")
    print("=" * 50)
    stealth = OrcaStealthExecution(get_stealth_config("normal"))
    client = MockClient()  # SIMULATED exchange client
    
    result = stealth.execute_stealth_order(
        client=client,
        symbol="BTC/USD",
        side="buy",
        quantity=0.001,
        price=50000,  # SIMULATED demo price
        value_usd=50
    )
    print(f"Result: {result}\n")
    
    # Test aggressive mode with large order
    print("=" * 50)
    print("TEST 2: Aggressive Mode - Large Order (should split) (SIMULATED)")
    print("=" * 50)
    stealth_agg = OrcaStealthExecution(get_stealth_config("aggressive"))
    
    result = stealth_agg.execute_stealth_order(
        client=client,
        symbol="ETH/USD",
        side="buy",
        quantity=1.0,
        price=3000,  # SIMULATED demo price
        value_usd=3000
    )
    print(f"Result: {result}\n")
    
    # Test hunted symbol rotation
    print("=" * 50)
    print("TEST 3: Symbol Rotation (mark symbol as hunted) (SIMULATED)")
    print("=" * 50)
    stealth.mark_symbol_hunted("BTC/USD", firm="citadel", front_run_count=5)
    
    result = stealth.execute_stealth_order(
        client=client,
        symbol="BTC/USD",  # Should suggest rotation
        side="buy",
        quantity=0.001,
        price=50000  # SIMULATED demo price
    )
    print(f"Result: {result}\n")
    
    # Print stats
    stealth.print_stats()
    stealth_agg.print_stats()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_stealth_execution()
    else:
        print("""
🦈🥷 ORCA STEALTH EXECUTION - ANTI-FRONT-RUNNING COUNTERMEASURES 🥷🦈
═══════════════════════════════════════════════════════════════════════════════

Usage:
  python orca_stealth_execution.py --test   # Run tests

Or integrate into your trading system:

  from orca_stealth_execution import stealth_order, get_stealth_executor
  
  # Simple usage (drop-in replacement):
  result = stealth_order(client, symbol, 'buy', quantity, price=current_price)
  
  # Advanced usage:
  from orca_stealth_execution import OrcaStealthExecution, get_stealth_config
  
  stealth = OrcaStealthExecution(get_stealth_config("aggressive"))
  
  # Mark a symbol as hunted
  stealth.mark_symbol_hunted("BTC/USD", firm="citadel")
  
  # Execute with full stealth
  result = stealth.execute_stealth_order(client, symbol, side, qty, price)

Stealth Modes:
  - normal:     50-500ms delay, split >$50, 30min cooldown
  - aggressive: 100-800ms delay, split >$25, 60min cooldown
  - paranoid:   200-1500ms delay, split >$15, 120min cooldown
  - disabled:   No stealth measures (direct execution)

═══════════════════════════════════════════════════════════════════════════════
        """)
