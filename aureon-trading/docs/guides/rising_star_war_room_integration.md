# 🌟 Rising Star War Room Integration

This document describes the integration of Rising Star Logic into the War Room mode.

## What's Changed

### 1. Enhanced LivePosition Dataclass
Added accumulation tracking fields:
- `accumulation_count`: Times we've added to position (DCA)
- `total_cost`: Total USD spent across all buys  
- `avg_entry_price`: Average entry price (cost basis)
- `rising_star_candidate`: Original RisingStarCandidate if applicable

### 2. New Logic in War Room Loop

#### PHASE 1: Scan Using Rising Star (replaces old scan)
```python
# OLD WAY (scan_entire_market):
opportunities = self.scan_entire_market(min_change_pct=0.3)
best = opportunities[0]

# NEW WAY (Rising Star 4-stage):
if hasattr(self, 'rising_star_scanner'):
    # Stage 1: Scan entire market with ALL intelligence
    candidates = self.rising_star_scanner.scan_entire_market(max_candidates=20)
    
    # Stage 2 + 3: Simulate top 4, pick best 2
    best_2 = self.rising_star_scanner.select_best_two(candidates)
    
    # Stage 4: Execute on best 2
    for candidate in best_2:
        pos_data = self.rising_star_scanner.execute_with_accumulation(candidate, amount)
        if pos_data:
            # Create LivePosition with Rising Star data
            pos = LivePosition(
                symbol=pos_data['symbol'],
                exchange=pos_data['exchange'],
                entry_price=pos_data['entry_price'],
                entry_qty=pos_data['entry_qty'],
                entry_cost=pos_data['entry_cost'],
                breakeven_price=...,
                target_price=...,
                client=...,
                # Rising Star fields:
                accumulation_count=0,
                total_cost=pos_data['total_cost'],
                avg_entry_price=pos_data['avg_entry_price'],
                rising_star_candidate=candidate
            )
            positions.append(pos)
```

#### PHASE 2: Accumulation Logic (NEW)
When monitoring positions, check if price dropped significantly and BUY MORE:

```python
for pos in positions[:]:
    current = all_prices.get(pos.symbol, 0)
    
    # Check if we should accumulate (DCA)
    if pos.accumulation_count < 3:  # Max 3 accumulations
        price_drop_pct = ((current - pos.avg_entry_price) / pos.avg_entry_price) * 100
        
        # If dropped 5% or more, BUY MORE
        if price_drop_pct <= -5.0:
            # Calculate new buy amount (smaller than initial)
            accumulation_amount = amount_per_position * 0.5  # Half size
            
            try:
                # Place accumulation buy
                buy_order = pos.client.place_market_order(
                    symbol=pos.symbol,
                    side='buy',
                    quote_qty=accumulation_amount
                )
                
                if buy_order:
                    new_qty = float(buy_order.get('filled_qty', 0))
                    new_price = float(buy_order.get('filled_avg_price', current))
                    
                    # Update position with accumulated data
                    pos.accumulation_count += 1
                    pos.entry_qty += new_qty
                    pos.total_cost += new_price * new_qty * (1 + fee_rate)
                    pos.avg_entry_price = pos.total_cost / pos.entry_qty
                    
                    # Recalculate breakeven and target based on NEW avg entry
                    pos.breakeven_price = pos.avg_entry_price * (1 + fee_rate) / (1 - fee_rate)
                    pos.target_price = pos.breakeven_price * (1 + target_pct / 100)
                    
                    print(f"🔄 ACCUMULATED {pos.symbol}: {new_qty:.4f} @ ${new_price:.2f}")
                    print(f"   New Avg Entry: ${pos.avg_entry_price:.2f}")
                    print(f"   Total Qty: {pos.entry_qty:.4f}")
            except Exception as e:
                print(f"Accumulation failed: {e}")
    
    # Calculate P&L based on AVERAGE entry price
    exit_value = current * pos.entry_qty * (1 - fee_rate)
    net_pnl = exit_value - pos.total_cost
    
    # Update position
    pos.current_price = current
    pos.current_pnl = net_pnl
```

#### PHASE 3: 30-Second Optimization (NEW)
Track time in position and prioritize fast exits:

```python
for pos in positions[:]:
    # Calculate time in position
    time_in_position = (time.time() - pos.entry_time.timestamp())
    
    # Check if profitable AND within 30-second window
    if net_pnl > 0 and time_in_position <= 30:
        # FAST KILL - met 30-second target!
        sell_order = pos.client.place_market_order(
            symbol=pos.symbol,
            side='sell',
            quantity=pos.entry_qty
        )
        if sell_order:
            session_stats['rising_star_30s_wins'] += 1
            warroom.record_kill(net_pnl)
            positions.remove(pos)
    
    # Or if past 30s but profitable at target
    elif net_pnl > 0 and current >= pos.target_price:
        # Standard profitable exit
        sell_order = ...
```

## How to Enable

In your War Room mode startup, add:

```python
from aureon_rising_star_logic import integrate_rising_star_logic

# Enable Rising Star Logic
integrate_rising_star_logic(self)  # Pass OrcaKillCycle instance

print("🌟 Rising Star Logic: ACTIVE")
```

## Expected Behavior

### Old Way (24% win rate):
1. Scan market
2. Pick best opportunity
3. Buy once
4. Wait for +1% target
5. Sell
6. Never accumulate if price drops

### New Way (Rising Star + Accumulation):
1. **SCAN**: Use ALL intelligence systems (quantum, probability, wave, firms)
2. **SIMULATE**: Run 1000 Monte Carlo sims on top 4 candidates
3. **SELECT**: Pick best 2 based on win rate + speed
4. **EXECUTE**: Open positions on best 2
5. **ACCUMULATE**: If price drops 5% → BUY MORE (DCA)
6. **OPTIMIZE**: Target 30-second profit window
7. **EXIT**: Sell entire accumulated stack when profitable

## Math Example

### Without Accumulation (Old):
- Buy $5.00 worth at $350
- Price drops to $340 (-2.86%)
- Fees: $0.025 (0.5% round-trip)
- Sell at $350: **LOSS $0.025**

### With Accumulation (New - Rising Star):
- Buy #1: $5.00 at $350 = 0.0143 units
- Price drops to $340 (-2.86%)
- Buy #2: $2.50 at $340 = 0.0074 units
- **Total**: 0.0217 units @ $346.55 avg entry
- Price recovers to $350 (+1.00% from avg)
- Sell: $7.50 value - $0.0375 fees = **PROFIT $0.10**

The accumulation WINS even when price barely recovers!

## Monitoring

Track these new metrics:
- `rising_star_30s_wins`: Exits within 30-second window
- `accumulation_total`: Total times we've added to positions
- `avg_accumulations_per_win`: How many DCA buys per winning trade
- `rising_star_confidence_avg`: Average simulation confidence

## Files Modified

1. `orca_complete_kill_cycle.py` - Enhanced LivePosition dataclass
2. `aureon_rising_star_logic.py` - NEW file with 4-stage system
3. War Room loop - Add accumulation logic (lines ~5100-5250)
