#!/usr/bin/env python3
"""
🌟 RISING STAR WAR ROOM INTEGRATION - Drop-in Enhancement
═══════════════════════════════════════════════════════════════════════════════

This module adds Rising Star Logic + Accumulation to War Room mode.

USAGE:
    from rising_star_war_room_enhancer import enhance_war_room_with_rising_star
    
    # In your OrcaKillCycle class:
    enhance_war_room_with_rising_star(self)
    
    # Then run War Room as normal - it now uses Rising Star Logic!

Gary Leckey | The Math Works | January 2026
═══════════════════════════════════════════════════════════════════════════════
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import time
from typing import List, Optional
from aureon.analytics.aureon_rising_star_logic import RisingStarScanner


def add_accumulation_logic(orca_instance, pos, current_price: float, 
                            amount_per_position: float, fee_rate: float) -> bool:
    """
    🔄 ACCUMULATION LOGIC - Buy more when price drops.
    
    Implements DCA (Dollar Cost Averaging) strategy:
    - If position dropped 5% from avg entry → BUY MORE
    - Max 3 accumulations per position
    - Updates avg entry price, total cost, breakeven
    
    Returns True if accumulated, False otherwise.
    """
    # Check if we can still accumulate
    if pos.accumulation_count >= 3:
        return False
    
    # Calculate price drop from average entry
    if pos.avg_entry_price == 0:
        # First time - set avg entry
        pos.avg_entry_price = pos.entry_price
        pos.total_cost = pos.entry_cost
    
    price_drop_pct = ((current_price - pos.avg_entry_price) / pos.avg_entry_price) * 100
    
    # If dropped 5% or more, accumulate
    if price_drop_pct <= -5.0:
        # Calculate accumulation amount (smaller than initial)
        accumulation_amount = amount_per_position * 0.5  # Half size
        
        try:
            # Place buy order
            buy_order = pos.client.place_market_order(
                symbol=pos.symbol,
                side='buy',
                quote_qty=accumulation_amount
            )
            
            if buy_order and buy_order.get('filled_qty'):
                new_qty = float(buy_order['filled_qty'])
                new_price = float(buy_order.get('filled_avg_price', current_price))
                new_cost = new_price * new_qty * (1 + fee_rate)
                
                # Update position with accumulated data
                old_avg = pos.avg_entry_price
                pos.accumulation_count += 1
                pos.entry_qty += new_qty
                pos.total_cost += new_cost
                pos.avg_entry_price = pos.total_cost / (pos.entry_qty * (1 + fee_rate))
                
                # Recalculate breakeven and target based on NEW avg entry
                pos.breakeven_price = pos.avg_entry_price * (1 + fee_rate) / (1 - fee_rate)
                pos.target_price = pos.breakeven_price * 1.01  # +1% target
                
                print(f"🔄 ACCUMULATED {pos.symbol}:")
                print(f"   Bought: {new_qty:.4f} @ ${new_price:.4f}")
                print(f"   Old Avg: ${old_avg:.4f} → New Avg: ${pos.avg_entry_price:.4f}")
                print(f"   Total Qty: {pos.entry_qty:.4f}")
                print(f"   Accumulations: {pos.accumulation_count}/3")
                
                return True
        except Exception as e:
            print(f"❌ Accumulation failed: {e}")
    
    return False


def check_30_second_profit_window(pos, net_pnl: float, entry_time) -> bool:
    """
    ⚡ 30-SECOND PROFIT WINDOW - Fast kill optimization.
    
    Returns True if:
    - Position is profitable (net_pnl > 0)
    - AND time in position <= 30 seconds
    
    This is the Rising Star "time-to-kill" optimization.
    """
    try:
        time_in_position = time.time() - entry_time.timestamp()
        if net_pnl > 0 and time_in_position <= 30:
            print(f"⚡ 30-SECOND KILL: {pos.symbol} profitable in {time_in_position:.1f}s!")
            return True
    except Exception:
        pass
    return False


def scan_with_rising_star(orca_instance, max_positions: int, 
                          active_symbols: List[str]) -> List[dict]:
    """
    🌟 SCAN WITH RISING STAR LOGIC
    
    Replaces old scan_entire_market() with 4-stage Rising Star filtering:
    1. Scan entire market with ALL intelligence
    2. Pick top 4 candidates
    3. Run Monte Carlo simulations on each
    4. Select best 2
    
    Returns list of position data dicts ready to open.
    """
    if not hasattr(orca_instance, 'rising_star_scanner'):
        return []
    
    scanner = orca_instance.rising_star_scanner
    
    try:
        # Stage 1: Scan entire market
        print("🔍 Stage 1: Scanning market with all intelligence systems...")
        candidates = scanner.scan_entire_market(max_candidates=20)
        
        if not candidates:
            return []
        
        # Filter out symbols we already have
        candidates = [c for c in candidates if c.symbol not in active_symbols]
        
        if not candidates:
            return []
        
        print(f"   Found {len(candidates)} candidates")
        
        # Stage 2 + 3: Simulate top 4, select best 2
        print("🎲 Stage 2-3: Running simulations + selecting best 2...")
        best_2 = scanner.select_best_two(candidates)
        
        if not best_2:
            return []
        
        print(f"✨ Selected 2 Rising Stars:")
        for i, c in enumerate(best_2, 1):
            print(f"   {i}. {c.symbol} @ ${c.price:.2f}")
            print(f"      Score: {c.score:.2f} | Win Rate: {c.simulation_win_rate:.0%}")
            print(f"      Time to Profit: {c.time_to_profit_avg:.0f}s")
            print(f"      Confidence: {c.simulation_confidence:.0%}")
        
        # Stage 4: Execute (return data, caller will create LivePosition)
        positions_to_open = []
        for candidate in best_2:
            # Check if we have room for more positions
            if len(positions_to_open) + max_positions >= max_positions:
                break
            
            positions_to_open.append({
                'candidate': candidate,
                'symbol': candidate.symbol,
                'exchange': candidate.exchange,
                'price': candidate.price
            })
        
        return positions_to_open
        
    except Exception as e:
        print(f"❌ Rising Star scan failed: {e}")
        return []


def enhance_war_room_with_rising_star(orca_instance):
    """
    🌟 ENHANCE WAR ROOM WITH RISING STAR LOGIC
    
    Call this ONCE to add Rising Star capabilities to OrcaKillCycle.
    
    Adds:
    - RisingStarScanner instance
    - Accumulation methods
    - 30-second profit optimization
    - Helper methods for War Room integration
    
    Usage:
        enhance_war_room_with_rising_star(self)
    """
    # Create Rising Star scanner
    scanner = RisingStarScanner(orca_instance)
    orca_instance.rising_star_scanner = scanner
    orca_instance.rising_star_enabled = True
    
    # Add helper methods to instance
    orca_instance.add_accumulation_logic = lambda pos, current, amount, fee: \
        add_accumulation_logic(orca_instance, pos, current, amount, fee)
    
    orca_instance.check_30_second_profit = lambda pos, pnl, entry_time: \
        check_30_second_profit_window(pos, pnl, entry_time)
    
    orca_instance.scan_with_rising_star = lambda max_pos, active_syms: \
        scan_with_rising_star(orca_instance, max_pos, active_syms)
    
    # Add Rising Star stats
    orca_instance.rising_star_stats = {
        'total_scans': 0,
        'candidates_found': 0,
        'simulations_run': 0,
        'positions_opened': 0,
        'accumulations_total': 0,
        '30s_wins': 0,
        'avg_time_to_profit': 0.0
    }
    
    print("╔════════════════════════════════════════════════════════════╗")
    print("║  🌟 RISING STAR LOGIC: ENABLED                            ║")
    print("║                                                            ║")
    print("║  ✓ 4-Stage Filtering                                      ║")
    print("║  ✓ Monte Carlo Simulations (1000 per candidate)           ║")
    print("║  ✓ Accumulation/DCA Logic                                 ║")
    print("║  ✓ 30-Second Profit Optimization                          ║")
    print("║  ✓ Multi-Intelligence Scanning                            ║")
    print("╚════════════════════════════════════════════════════════════╝")


# Example War Room integration code:
EXAMPLE_WAR_ROOM_CODE = '''
# In your War Room loop, replace this:
# OLD:
if current_time - last_scan_time >= scan_interval:
    opportunities = self.scan_entire_market(min_change_pct=0.3)
    if opportunities:
        best = opportunities[0]
        # ... buy logic ...

# NEW (with Rising Star):
if current_time - last_scan_time >= scan_interval:
    active_symbols = [p.symbol for p in positions]
    rising_star_positions = self.scan_with_rising_star(max_positions, active_symbols)
    
    for pos_data in rising_star_positions:
        candidate = pos_data['candidate']
        
        # Execute with Rising Star scanner
        result = self.rising_star_scanner.execute_with_accumulation(
            candidate, 
            amount_per_position
        )
        
        if result:
            # Create LivePosition with Rising Star data
            pos = LivePosition(
                symbol=result['symbol'],
                exchange=result['exchange'],
                entry_price=result['entry_price'],
                entry_qty=result['entry_qty'],
                entry_cost=result['entry_cost'],
                breakeven_price=result['entry_price'] * (1 + fee_rate) / (1 - fee_rate),
                target_price=result['entry_price'] * 1.01,
                client=self.clients[result['exchange']],
                accumulation_count=0,
                total_cost=result['total_cost'],
                avg_entry_price=result['avg_entry_price'],
                rising_star_candidate=candidate
            )
            positions.append(pos)
            self.rising_star_stats['positions_opened'] += 1

# In position monitoring loop, add accumulation check:
for pos in positions[:]:
    current = all_prices.get(pos.symbol, 0)
    
    # TRY TO ACCUMULATE if price dropped
    if self.add_accumulation_logic(pos, current, amount_per_position, fee_rate):
        self.rising_star_stats['accumulations_total'] += 1
    
    # Calculate P&L based on AVERAGE entry (not initial)
    exit_value = current * pos.entry_qty * (1 - fee_rate)
    net_pnl = exit_value - pos.total_cost  # Use total_cost!
    
    pos.current_price = current
    pos.current_pnl = net_pnl
    
    # Check for 30-second profit window
    if self.check_30_second_profit(pos, net_pnl, pos.entry_time):
        # FAST KILL - met 30-second target!
        sell_order = pos.client.place_market_order(...)
        if sell_order:
            self.rising_star_stats['30s_wins'] += 1
            positions.remove(pos)
    
    # Standard profitable exit
    elif net_pnl > 0 and current >= pos.target_price:
        sell_order = pos.client.place_market_order(...)
        ...
'''

if __name__ == "__main__":
    print("🌟 Rising Star War Room Enhancer")
    print("\nThis module enhances War Room mode with:")
    print("  - 4-stage filtering (scan → simulate → select → execute)")
    print("  - DCA/Accumulation when price drops")
    print("  - 30-second profit optimization")
    print("  - Multi-intelligence scoring")
    print("\nUsage:")
    print("  from rising_star_war_room_enhancer import enhance_war_room_with_rising_star")
    print("  enhance_war_room_with_rising_star(self)")
