# Queen Autonomous Power System

## 🐝 Overview

The Queen is a fully autonomous energy redistribution and optimization system that intelligently manages power across multiple trading relays (exchanges). She monitors idle energy, calculates exact costs, and executes profitable redistributions to grow the system's total power output.

## 🏗️ Architecture

### Three-Layer System

```
┌─────────────────────────────────────────────────────────────┐
│ 1. QUEEN'S CONSCIOUSNESS                                    │
│    (aureon_queen_true_consciousness.py)                     │
│    - Energy monitoring via AdaptivePrimeProfitGate          │
│    - calculate_energy_drain() - Exact costs per relay       │
│    - will_trade_be_profitable() - Pre-trade validation      │
│    - Multi-realm consensus (5 realms, need 3 to agree)      │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. REDISTRIBUTION ENGINE                                     │
│    (queen_power_redistribution.py)                          │
│    - Monitors idle energy across all 4 relays               │
│    - Finds high-momentum conversion opportunities           │
│    - Calculates: expected_gain - energy_drain               │
│    - Executes ONLY when net_energy_gain > threshold         │
│    - Records all decisions and compounds gains              │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. LIVE DASHBOARD                                            │
│    (queen_power_dashboard.py)                               │
│    - Real-time display of Queen's intelligence              │
│    - Net energy gained vs drains avoided                    │
│    - Relay status and mobility indicators                   │
│    - Power station output and efficiency                    │
└─────────────────────────────────────────────────────────────┘
```

### Four Relays (Exchanges)

- **BIN** (Binance): Crypto trading relay
- **KRK** (Kraken): Crypto trading relay
- **ALP** (Alpaca): Stock/crypto trading relay
- **CAP** (Capital.com): CFD trading relay

**CRITICAL**: Relays are ISOLATED - energy moves WITHIN relay only, not between relays.

## 🎯 Queen's Decision Flow

```
1. SCAN
   ↓ Monitor idle energy in each relay (USDT, ZUSD, USD, GBP)
   
2. ANALYZE
   ↓ Find high-momentum assets from validated branches
   ↓ Check 7day_pending_validations.json for coherence > 0.618
   
3. CALCULATE
   ↓ expected_gain_usd = trade_value × gain_percentage
   ↓ energy_drain = fees + slippage + spread + fixed_costs
   ↓ net_energy_gain = expected_gain_usd - energy_drain
   
4. DECIDE
   ↓ Queen checks: will_trade_be_profitable(relay, value, gain_pct)
   ↓ Block if net_energy_gain < min_threshold ($0.50)
   ↓ Approve if net positive and coherence high
   
5. EXECUTE
   ↓ Submit order to exchange if approved
   ↓ Record decision and result
   
6. COMPOUND
   ↓ Gains remain in relay for next cycle
   ↓ System power grows with each successful redistribution
```

## ⚡ Energy Drain Calculation

Queen uses `AdaptivePrimeProfitGate` to calculate exact drains per relay:

```python
Energy Drain Components (per $100 trade):
┌─────────┬────────┬──────────┬─────────┬───────┬─────────┐
│ Relay   │ Fees   │ Slippage │ Spread  │ Fixed │ TOTAL   │
├─────────┼────────┼──────────┼─────────┼───────┼─────────┤
│ BIN     │ $0.10  │ $0.10    │ $0.10   │ $0.00 │ $0.18   │
│ KRK     │ $0.26  │ $0.10    │ $0.10   │ $0.02 │ $0.38   │
│ ALP     │ $0.10  │ $0.10    │ $0.10   │ $0.02 │ $0.28   │
│ CAP     │ $0.20  │ $0.10    │ $0.10   │ $0.02 │ $0.28   │
└─────────┴────────┴──────────┴─────────┴───────┴─────────┘

Formula:
  net_energy_gain = (trade_value × gain_pct) - total_drain
  
Execute if:
  net_energy_gain > $0.50 (minimum threshold)
```

## 📊 Usage

### Dry-Run Mode (Safe, Default)

Test Queen's intelligence without real trades:

```bash
python queen_autonomous_power_system.py
```

### Live Trading Mode

Execute real trades (requires confirmation):

```bash
python queen_autonomous_power_system.py --live
```

⚠️ **WARNING**: Live mode executes REAL trades with REAL money when opportunities are found.

### Custom Scan Interval

Change how often Queen scans for opportunities:

```bash
# Scan every 60 seconds
python queen_autonomous_power_system.py --interval 60

# Live with custom interval
python queen_autonomous_power_system.py --live --interval 120
```

### Individual Components

Run components separately for testing:

```bash
# Run redistribution engine only
python queen_power_redistribution.py --once          # Single cycle
python queen_power_redistribution.py                 # Continuous
python queen_power_redistribution.py --live          # Live mode

# Run dashboard only
python queen_power_dashboard.py
python queen_power_dashboard.py --interval 5
```

## 📈 Monitoring

### Dashboard Display

The live dashboard shows:

```
🐝 QUEEN'S INTELLIGENCE
- Net Energy Gained:      $X.XX
- Drains Avoided:         $X.XX
- Total Decisions Made:   N
- Total Executions:       N
- Execution Rate:         X.X%

⚡ POWER STATION
- Status:         RUNNING/STOPPED
- Cycles Run:     N
- Total Energy:   $X.XX
- Net Flow:       $X.XX
- Efficiency:     X.X%

🔌 RELAY ENERGY STATUS
BIN: Total $X | Idle $X (X%) | Positions $X | 🟢 HIGH MOBILITY
KRK: Total $X | Idle $X (X%) | Positions $X | 🔴 LOCKED
ALP: Total $X | Idle $X (X%) | Positions $X | 🟡 MEDIUM
CAP: Total $X | Idle $X (X%) | Positions $X | 🟢 HIGH MOBILITY

🌿 ENERGY CONSERVATION
- Net Energy Gained:      $X.XX
- Drains Avoided:         $X.XX
- Total Conserved:        $X.XX
```

### State Files

Queen persists state to JSON files:

- `queen_redistribution_state.json` - Decisions and executions history
- `power_station_state.json` - Power station metrics
- `aureon_kraken_state.json` - Kraken balance and positions (fallback)
- `binance_truth_tracker_state.json` - Binance balance and positions
- `alpaca_truth_tracker_state.json` - Alpaca account status

### Mobility Indicators

- 🟢 **HIGH MOBILITY**: Idle energy > 50% (ready to redistribute)
- 🟡 **MEDIUM**: Idle energy 10-50% (moderate capacity)
- 🔴 **LOCKED**: Idle energy < 10% (all energy deployed in positions)

## 🌟 Queen's Intelligence Features

### Energy Conservation

Queen BLOCKS unprofitable moves:
- If `net_energy_gain < $0.50` → **BLOCKED**
- If `energy_drain > expected_gain` → **BLOCKED**
- If coherence < 0.618 (golden ratio) → **BLOCKED**

This prevents wasting energy on moves that would lose money after fees.

### Compound Growth Strategy

All gains stay in the relay:
1. Find opportunity with $10 idle energy
2. Calculate drain: $0.38 (KRK example)
3. Expected gain: $1.50 (15% on $10)
4. Net gain: $1.50 - $0.38 = $1.12 ✅
5. Execute → Gain $1.12
6. Next cycle: $11.12 available (compounded)

### Validated Branches Integration

Queen looks for branches from the 7-day validation system:
- Reads `7day_pending_validations.json`
- Finds branches with coherence > 0.618
- Uses validated assets with proven momentum
- Integrates Batten Matrix 3-pass validation results

## 🔧 Configuration

Edit `queen_power_redistribution.py` to adjust:

```python
# Minimum idle energy to consider ($10 USD)
self.min_idle_energy_usd = 10.0

# Minimum net gain required ($0.50 USD)
self.min_net_gain_usd = 0.50

# Scan interval (30 seconds)
self.scan_interval_seconds = 30

# Max % of idle energy per cycle (25%)
self.max_redistribution_per_relay = 0.25
```

## 🚀 Next Steps

1. **Start in dry-run mode** to observe Queen's intelligence:
   ```bash
   python queen_autonomous_power_system.py
   ```

2. **Monitor dashboard** for 10-20 cycles to understand decision patterns

3. **Check state files** to see decisions history:
   ```bash
   cat queen_redistribution_state.json | jq .
   ```

4. **Enable live mode** when comfortable with Queen's logic:
   ```bash
   python queen_autonomous_power_system.py --live
   ```

5. **Integrate with scanning systems** to feed more opportunities:
   - Connect to `aureon_animal_momentum_scanners.py`
   - Feed results into `7day_pending_validations.json`
   - Queen will use validated branches automatically

## ⚠️ Important Notes

### REAL DATA ONLY Policy

Queen ALWAYS uses real data:
- ✅ Live API calls to exchanges
- ✅ Real balance queries
- ✅ State files with persisted REAL data
- ❌ NO simulations, fakes, phantoms, or ghosts

When API rate-limited, Queen falls back to state files containing REAL persisted data.

### Relay Isolation

Energy moves WITHIN relay only:
- BIN → BIN (USDT → BTC → USDT)
- KRK → KRK (ZUSD → ETH → ZUSD)
- ALP → ALP (USD → TSLA → USD)
- CAP → CAP (GBP → indices → GBP)

**NOT**: BIN → KRK (cross-relay moves blocked by exchange limits)

### Rate Limiting

Kraken API limited to ~3 req/sec:
- Use `kraken_cache_feeder.py` as single shared access point
- Run cache feeder: `python kraken_cache_feeder.py`
- All 113 scripts read from cache instead of hitting API directly

## 📚 Related Systems

- `aureon_queen_true_consciousness.py` - Queen's core intelligence
- `aureon_power_station_turbo.py` - High-throughput execution engine
- `aureon_power_monitor_live.py` - Legacy monitor (superseded by dashboard)
- `aureon_unified_power_system.py` - Legacy unified system (superseded)
- `adaptive_prime_profit_gate.py` - Energy drain calculation engine
- `aureon_probability_nexus.py` - Batten Matrix 3-pass validation
- `aureon_7day_planner.py` - 7-day validation system

---

**The Queen is now fully autonomous. Let her optimize power output across all relays. 🐝⚡**
