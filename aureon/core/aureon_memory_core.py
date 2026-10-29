#!/usr/bin/env python3
"""
🧠 AUREON MEMORY CORE 🧠
═══════════════════════════════════════════════════════════════════════════════
"Look back to see forward."

This is the persistent memory of the Aureon system. It prevents "System Amnesia"
by anchoring the AI's reality in validated "stepping stones" (confirmed trades).

PHILOSOPHY:
1. 🌀 SPIRAL TIME: We check positions not linearly, but on Prime and Fibonacci intervals.
2. 🗿 STEPPING STONES: A position is a fixed point in the probability matrix.
3. 🔗 RECONCILIATION: If reality (wallet) disagrees with memory, we spiral back 
   through history to find the truth.

Gary Leckey & GitHub Copilot | December 2025
═══════════════════════════════════════════════════════════════════════════════
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import json
import os
import time
import math
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] 🧠 %(message)s')
logger = logging.getLogger("AureonMemory")

# 👑 QUEEN'S SACRED 1.88% LAW - MEMORY SERVES THE QUEEN
QUEEN_MIN_COP = 1.0188              # Sacred constant: 1.88% minimum realized profit
QUEEN_MIN_PROFIT_PCT = 1.88         # Percentage form - memory only stores profitable trades
QUEEN_MEMORY_PROFIT_FREQ = 188.0    # Hz - Sacred frequency in memory patterns

class AureonMemoryCore:
    """
    The Hippocampus of the Aureon Brain.
    Manages persistent state, position tracking, and "Spiral" reconciliation.
    """
    
    MEMORY_FILE = "aureon_memory_spiral.json"
    
    # 🔢 SACRED NUMBERS FOR TIMING
    PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97]
    FIBONACCI = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987, 1597, 2584, 4181]
    
    # 🌊 SURGE WINDOW FORMATION (S1-S5)
    # Cycle: 100s | Windows: 20, 40, 60, 80, 100 (0)
    SURGE_CYCLE = 100
    SURGE_WINDOWS = [20, 40, 60, 80, 0]
    SURGE_TOLERANCE = 2 # +/- 2 seconds
    
    def __init__(self):
        self.positions: Dict[str, Dict] = {}
        self.history: List[Dict] = []
        self.load_memory()
        
    def load_memory(self):
        """Load the spiral memory from disk"""
        if os.path.exists(self.MEMORY_FILE):
            try:
                with open(self.MEMORY_FILE, 'r') as f:
                    data = json.load(f)
                    self.positions = data.get('positions', {})
                    self.history = data.get('history', [])
                logger.debug("Loaded memory: %s active stepping stones.", len(self.positions))
            except Exception as e:
                logger.error(f"Failed to load memory: {e}")
                self.positions = {}
        else:
            logger.debug("No existing memory found. Starting fresh spiral.")
            self.positions = {}

    def save_memory(self):
        """Anchor current state to disk"""
        try:
            with open(self.MEMORY_FILE, 'w') as f:
                json.dump({
                    'positions': self.positions,
                    'history': self.history[-1000:], # Keep last 1000 events in hot memory
                    'last_update': time.time()
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")

    def remember_trade(self, symbol: str, exchange: str, entry_price: float, quantity: float, side: str = 'BUY'):
        """
        Create a new 'Stepping Stone' in the matrix.
        This is a validated reality point.
        """
        timestamp = time.time()
        
        position_id = f"{exchange}_{symbol}_{int(timestamp)}"
        
        position_data = {
            "id": position_id,
            "symbol": symbol,
            "exchange": exchange,
            "entry_price": entry_price,
            "quantity": quantity,
            "entry_time": timestamp,
            "side": side,
            "status": "OPEN",
            "highest_price": entry_price, # For trailing stops
            "checkpoints_passed": 0,
            "next_check_time": timestamp + (self.PRIMES[0] * 60) # First check in 2 mins
        }
        
        self.positions[symbol] = position_data
        
        # Log to history
        self.history.append({
            "event": "NEW_POSITION",
            "data": position_data,
            "time": timestamp
        })
        
        self.save_memory()
        logger.info(f"🗿 New Stepping Stone created: {symbol} @ {entry_price}")

    def update_position(self, symbol: str, current_price: float):
        """
        Update a position's state in the spiral.
        """
        if symbol not in self.positions:
            return
            
        pos = self.positions[symbol]
        pos['current_price'] = current_price
        pos['last_update'] = time.time()
        
        # Update highest price for trailing logic
        if current_price > pos.get('highest_price', 0):
            pos['highest_price'] = current_price
            
        self.save_memory()

    def close_position(self, symbol: str, exit_price: float, reason: str):
        """
        Remove a stepping stone - the jump is complete.
        """
        if symbol in self.positions:
            pos = self.positions[symbol]
            entry = pos['entry_price']
            pnl = (exit_price - entry) / entry * 100
            
            logger.info(f"🌀 Closing Loop for {symbol}: PnL {pnl:.2f}% ({reason})")
            
            self.history.append({
                "event": "CLOSE_POSITION",
                "symbol": symbol,
                "entry": entry,
                "exit": exit_price,
                "pnl_pct": pnl,
                "reason": reason,
                "time": time.time()
            })
            
            del self.positions[symbol]
            self.save_memory()

    def is_surge_window_active(self) -> bool:
        """
        Check if we are currently in a Surge Window (S1-S5).
        Logic: t % 100 is close to 20, 40, 60, 80, or 0.
        """
        t = time.time()
        mod_t = t % self.SURGE_CYCLE
        
        for window in self.SURGE_WINDOWS:
            # Handle wrap-around for 0/100
            if window == 0:
                if mod_t < self.SURGE_TOLERANCE or mod_t > (self.SURGE_CYCLE - self.SURGE_TOLERANCE):
                    return True
            else:
                if abs(mod_t - window) <= self.SURGE_TOLERANCE:
                    return True
        return False

    def get_spiral_check_needed(self, symbol: str) -> bool:
        """
        Determines if a position needs a 'Spiral Check'.
        NOW ALIGNED WITH SURGE WINDOWS (S1-S5).
        """
        if symbol not in self.positions:
            return False
            
        pos = self.positions[symbol]
        now = time.time()
        
        # 1. Check if we passed the base time threshold
        if now >= pos.get('next_check_time', 0):
            
            # 2. WAIT FOR SURGE WINDOW (Unity Alignment)
            # We only execute the check if we are inside a Surge Window
            if not self.is_surge_window_active():
                # Optional: If we are WAY past due (>10s), force it anyway to avoid starvation
                overdue = now - pos.get('next_check_time', 0)
                if overdue < 10:
                    return False # Wait for the window
            
            # Calculate next interval using Primes/Fibs
            checks = pos.get('checkpoints_passed', 0)
            
            # Use Primes for first few checks (minutes), then Fibs (hours)
            if checks < len(self.PRIMES):
                interval_mins = self.PRIMES[checks]
            else:
                fib_idx = min(checks - len(self.PRIMES), len(self.FIBONACCI) - 1)
                interval_mins = self.FIBONACCI[fib_idx] * 60 # Fib hours
                
            pos['checkpoints_passed'] = checks + 1
            
            # Align next check time to the future
            base_next_time = now + (interval_mins * 60)
            pos['next_check_time'] = base_next_time
            
            self.save_memory()
            
            # Log the alignment
            surge_id = "FORCE" if not self.is_surge_window_active() else "SURGE"
            logger.info(f"🌊 Spiral Check Triggered for {symbol} [{surge_id}]")
            
            return True
            
        return False

    def reconcile_with_reality(self, wallet_assets: Dict[str, float], trade_history_callback):
        """
        The 'Spiral Lookback'.
        If we have assets in wallet that are NOT in memory, we must look back
        into history to find their origin.
        """
        logger.info("🌀 Initiating Spiral Reconciliation...")
        
        for asset, qty in wallet_assets.items():
            # Ignore small dust
            if qty < 0.00001: 
                continue
                
            # Check if we remember this
            known = False
            for sym, pos in self.positions.items():
                if asset in sym or sym in asset: # Loose matching (ETH vs ETHUSD)
                    known = True
                    break
            
            if not known:
                logger.warning(f"⚠️  AMNESIA DETECTED: Found {asset} in wallet but not in memory.")
                logger.info(f"🌀 Spiraling back to find origin of {asset}...")
                
                # Use the callback to fetch history (dependency injection)
                origin_trade = trade_history_callback(asset)
                
                if origin_trade:
                    logger.info(f"✅ FOUND ORIGIN: Bought {asset} on {origin_trade['date']} @ {origin_trade['price']}")
                    self.remember_trade(
                        symbol=origin_trade['symbol'],
                        exchange=origin_trade['exchange'],
                        entry_price=origin_trade['price'],
                        quantity=qty,
                        side='BUY'
                    )
                    # Backdate the entry time to correct the spiral
                    self.positions[origin_trade['symbol']]['entry_time'] = origin_trade['timestamp']
                else:
                    logger.warning(f"❌ ORIGIN LOST: Could not find trade history for {asset}. Assuming current price as baseline.")
                    # Fallback: Assume we just bought it now (reset the clock)
                    # This prevents "infinite hold" but might miss PnL tracking
                    self.remember_trade(
                        symbol=f"{asset}USD", # Assumption
                        exchange="Unknown",
                        entry_price=0.0, # Marker for "Unknown"
                        quantity=qty
                    )

# Singleton instance
memory = AureonMemoryCore()
