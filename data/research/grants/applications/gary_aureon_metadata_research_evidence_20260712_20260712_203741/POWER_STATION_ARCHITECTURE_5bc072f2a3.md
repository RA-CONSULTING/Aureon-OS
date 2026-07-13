# ⚡ AUREON POWER STATION - Energy-Focused Architecture

## Overview

The **Aureon Power Station** is the PRIMARY user interface for the Aureon Trading System. Unlike traditional trading dashboards that focus on financial metrics, the Power Station presents **everything as energy** - energy reserves, energy generation, energy consumption, and energy flows across the system.

## 🌌 Core Philosophy: Energy-Centric View

Traditional trading systems show:
- **Balances** in USD
- **Profit/Loss** in dollars
- **Trades** as buy/sell orders
- **Fees** as costs

The Power Station transforms this to:
- **Energy Reserves** (idle capital = potential energy)
- **Energy Generation** (profitable trades = energy created)
- **Energy Consumption** (losses/fees = energy drains)
- **Energy Redistribution** (trades = energy flow between states)

## 🏗️ System Architecture

### Port Configuration
- **Port 8080**: Queen Power Station (PRIMARY - Public Interface)
- **Port 8800**: Command Center (SECONDARY - Internal Operations)

### Process Hierarchy (supervisord priorities)
```
1. ⚡ Queen Power Station (pri 1)    - PRIMARY interface, shows energy flows
2. 🔄 Kraken Cache (pri 5)            - Data feed optimization
3. 🦈 Orca Kill Cycle (pri 10)        - Energy redistribution execution
4. 🧠 Autonomous Engine (pri 20)      - 9 intelligence loops
5. 🐝 Queen Redistribution (pri 25)   - Autonomous energy optimization
6. 👑 Command Center (pri 50)         - Internal operations dashboard
```

## ⚡ Queen Power Station Interface

### What You See

#### 1. **Header - Total System Energy**
```
╔══════════════════════════════════════════════════════════════════════════════╗
║  ⚡ AUREON POWER STATION - PRIMARY ENERGY INTERFACE                          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  📅 2026-01-25 01:03:50  ⏱️  Runtime: 5m 23s     🔄 Cycle: #47    ║
╠──────────────────────────────────────────────────────────────────────────────╣
║  💎 Total System Energy: $1,247.58 ⚡📈 Growth: +$154.92 (+14.18%)  ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

**Metrics:**
- **Total System Energy**: Sum of all capital across 4 relays (BIN, KRK, ALP, CAP)
- **Energy Growth**: Change from baseline (startup state)
- **Growth Percentage**: Rate of energy accumulation

**Indicators:**
- ⚡📈 Green = Energy increasing
- ⚠️📉 Red = Energy draining
- ⚡━ Yellow = Energy stable

---

#### 2. **Queen Energy Generation Intelligence**
Shows Queen's autonomous decision-making and energy optimization:

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  🐝 QUEEN ENERGY GENERATION INTELLIGENCE                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝

  ⚡ Engine Status:       💚 ACTIVE (updated 23s ago)

  📊 Energy Generation Summary:
     ├─ ⚡ Energy Generated:      $47.82          (Net positive moves)
     ├─ 🛡️  Energy Conserved:      $12.45          (Blocked drains)
     └─ 💎 Total Energy Impact:   $60.27

  🎯 Queen Performance:
     ├─ Decisions Analyzed:      142 opportunities
     ├─ Energy Moves Executed:   23 redistributions
     └─ Efficiency:              $0.42 per decision

  📊 Recent Energy Decisions:
     ├─ ✅ EXECUTE   │ CAP → BTC/USD      │ $2.15        │ ●●●●○
     ├─ 🚫 BLOCK     │ KRK → ETH/USD      │ -$0.87       │ ●●○○○
     └─ ✅ EXECUTE   │ ALP → AAPL         │ $1.34        │ ●●●●●
```

**Heartbeat:**
- 💚 ACTIVE = Engine running, updated recently
- 💔 IDLE = No recent activity

**Energy Metrics:**
- **Energy Generated**: Sum of all profitable moves (net positive after fees)
- **Energy Conserved**: Losses prevented by blocking unprofitable trades
- **Total Impact**: Generated + Conserved = Queen's value contribution

**Efficiency:**
- **Per Decision**: Average energy gained/conserved per opportunity analyzed
- Higher = Queen making better choices

**Recent Decisions:**
- ✅ EXECUTE = Queen approved energy move
- 🚫 BLOCK = Queen prevented energy drain
- Confidence bars (●●●●●) = Queen's certainty (0-100%)

---

#### 3. **Energy Reserves & Flow**
System-wide energy status:

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  ⚡ ENERGY RESERVES & FLOW                                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝

  🟢 Power Station Status:  RUNNING  (487 energy cycles)

  💎 System Energy Status:
     ├─ Total Energy Reserves:    $1,247.58
     ├─ Energy in Positions:      $342.12
     └─ Net Energy Flow (24h):    +$47.82

  📊 Energy Efficiency:         78.4% [████████░░]
```

**Status:**
- 🟢 RUNNING = Power station operational
- 🟡 STOPPED = Power station idle

**Energy Breakdown:**
- **Total Reserves**: All available capital (idle + deployed)
- **In Positions**: Energy currently deployed in active trades
- **Net Flow (24h)**: Energy gained/lost in last 24 hours

**Efficiency:**
- Percentage of energy moves that result in net gain
- Progress bar shows visual efficiency level

---

#### 4. **Energy Distribution by Relay**
How energy is distributed across the 4 independent exchange relays:

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  🔌 ENERGY DISTRIBUTION BY RELAY                                            ║
╚══════════════════════════════════════════════════════════════════════════════╝

  (Each relay operates independently with internal energy isolation)

  RELAY      TOTAL        IDLE         DEPLOYED     MOBILITY            
  ──────────────────────────────────────────────────────────────────────────
  BIN        $247.58      $124.30      $123.28      🟢 HIGH [█████] 50%
  KRK        $512.34      $487.12      $25.22       🟢 HIGH [█████] 95%
  ALP        $342.18      $87.45       $254.73      🟡 MED [███░░] 26%
  CAP        $145.48      $145.48      $0.00        🟢 HIGH [█████] 100%
  ──────────────────────────────────────────────────────────────────────────
  TOTAL      $1,247.58    $844.35      $403.23      ⚡ System: 68% idle
```

**Relays:**
- **BIN** = Binance
- **KRK** = Kraken
- **ALP** = Alpaca
- **CAP** = Capital.com

**Energy States:**
- **TOTAL**: All energy in relay (idle + deployed)
- **IDLE**: Energy available for redistribution
- **DEPLOYED**: Energy in active positions

**Mobility:**
Percentage of energy that is idle (available to move):
- 🟢 HIGH (>50%) = Lots of energy ready to redistribute
- 🟡 MED (10-50%) = Some energy available
- 🔴 LOW (<10%) = Most energy locked in positions

---

#### 5. **Energy Conservation & Generation**
Summary of Queen's energy optimization:

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  🌿 ENERGY CONSERVATION & GENERATION                                        ║
╚══════════════════════════════════════════════════════════════════════════════╝

  💎 Net Energy Gained:        $47.82
  🛡️  Drains Blocked:           $12.45
  ✨ Total Conserved:           $60.27

  📈 Begin trading to track conservation metrics
```

**Metrics:**
- **Net Energy Gained**: Cumulative profit from all executed trades
- **Drains Blocked**: Losses prevented by rejecting bad opportunities
- **Total Conserved**: Sum of gained + blocked = Queen's total value add

---

## 🔄 Energy Flow Architecture

### How Energy Moves Through the System

```
[Market Data] → [Scanner Eyes] → [Brain Analysis] → [Queen Decision]
                                                            ↓
[Relay Energy Idle] ← [Energy Redistribution] ← [Orca Execution]
         ↓
[Deployed Position] → [Energy Generation/Consumption] → [Back to Idle]
```

### Energy States

1. **Idle Energy (Reserves)**
   - Capital sitting in exchange accounts
   - Available for immediate redistribution
   - Shows as "IDLE" in relay status
   - High mobility = good (ready to move)

2. **Deployed Energy (Positions)**
   - Capital in active trades
   - Locked until position closes
   - Shows as "DEPLOYED" in relay status
   - Lower mobility = energy in use

3. **Energy Generation (Profit)**
   - Successful trade closes above entry
   - Net gain after all fees/spreads
   - Added to "Energy Generated" metric
   - Returns to idle state with more energy

4. **Energy Consumption (Loss)**
   - Trade closes below entry
   - Net loss including fees/spreads
   - Tracked but NOT shown (focus on positive)
   - Returns to idle state with less energy

---

## 🐝 Queen's Energy Optimization

The **Queen Hive Mind** is the autonomous intelligence that optimizes energy flow:

### Decision Process

1. **Opportunity Scan** (every 60s)
   - Scans all 4 relays for idle energy
   - Identifies potential redistribution moves
   - Calculates expected energy gain/drain for each

2. **Queen Analysis**
   - Evaluates each opportunity with:
     - `calculate_energy_drain()` - Estimated energy consumed by fees/spreads
     - `will_trade_be_profitable()` - Net energy gain prediction
   - Only considers moves with **net positive energy** (gain - drain > $0.50)

3. **Execution Gate**
   - Approved moves sent to Orca Kill Cycle
   - Orca executes energy redistribution
   - State files updated with outcome
   - Dashboard shows decision in "Recent Energy Decisions"

4. **Learning & Adaptation**
   - Tracks all decisions and outcomes
   - Updates efficiency metrics
   - Improves future energy predictions

### Queen's Intelligence

The Queen doesn't just trade - she **optimizes energy flow**:
- **Blocks drains**: Rejects unprofitable opportunities (conserves energy)
- **Generates energy**: Executes only high-confidence positive moves
- **Tracks efficiency**: Learns from all decisions to improve
- **Autonomous**: No human intervention required

---

## 📊 Real-Time Updates

The Power Station updates every **5 seconds** with:
- Latest system energy totals
- Queen's most recent decisions
- Energy distribution changes
- Relay mobility shifts
- Energy generation metrics

All data is pulled from state files:
- `power_station_state.json` - Station metrics
- `queen_redistribution_state.json` - Queen decisions
- `queen_energy_balance.json` - Energy totals
- `{relay}_state.json` - Per-relay data

---

## 🚀 Deployment

### Digital Ocean Configuration

**Region**: London (lon)  
**Instance**: professional-xs (1GB RAM, 0.5 vCPU)  
**Auto-deploy**: Enabled from `main` branch

**Ports:**
- **8080**: Queen Power Station (PRIMARY)
- **8800**: Command Center (SECONDARY)

### Process Startup Order

supervisord starts processes in priority order:

1. **Queen Power Station** (pri 1) - Interface starts first, shows "STOPPED" state
2. **Kraken Cache** (pri 5) - Begins feeding market data
3. **Orca Kill Cycle** (pri 10) - Execution engine ready
4. **Autonomous Engine** (pri 20) - Intelligence loops start
5. **Queen Redistribution** (pri 25) - Begins analyzing opportunities
6. **Command Center** (pri 50) - Internal dashboard ready

Within ~30 seconds, all systems are operational and Power Station shows "RUNNING".

---

## 🎯 Key Differences from Command Center

| Feature | Power Station (8080) | Command Center (8800) |
|---------|---------------------|----------------------|
| **Primary Focus** | Energy flows & optimization | System internals & diagnostics |
| **Metrics** | Energy reserves, generation, conservation | Bot counts, scanner status, API health |
| **User Type** | End users, traders | Developers, system admins |
| **Update Rate** | 5 seconds | 3 seconds |
| **View** | Energy-centric (all in energy terms) | Technical (raw system metrics) |
| **Priority** | 1 (starts first) | 50 (starts last) |

---

## 📈 Energy Growth Tracking

The Power Station calculates **Energy Growth** by:

1. **Baseline Capture** (on startup):
   ```python
   baseline = get_total_system_energy()
   # Stored in self.total_energy_at_start
   ```

2. **Current Energy** (every cycle):
   ```python
   current = get_total_system_energy()
   ```

3. **Growth Calculation**:
   ```python
   energy_growth = current - baseline
   growth_percentage = (energy_growth / baseline) * 100
   ```

4. **Display**:
   - Green ⚡📈 if growing
   - Red ⚠️📉 if declining
   - Yellow ⚡━ if stable

This shows the system's **net energy generation over time** - the ultimate measure of success.

---

## 🔧 Configuration

### State Files

All energy data persists in JSON state files:

- **`power_station_state.json`**: Station status, cycles, efficiency
- **`queen_redistribution_state.json`**: Decisions, executions, energy impact
- **`queen_energy_balance.json`**: Total energy reserves
- **`BIN_state.json`**: Binance relay energy
- **`KRK_state.json`**: Kraken relay energy
- **`ALP_state.json`**: Alpaca relay energy
- **`CAP_state.json`**: Capital relay energy

### Environment Variables

```bash
PORT=8080                           # Power Station port
AUREON_STATE_DIR=/app/state         # State file directory
```

### Update Interval

```bash
python queen_power_dashboard.py --interval 5
# Updates display every 5 seconds
```

---

## 🎨 Visual Design Elements

The Power Station uses professional box-drawing characters for clarity:

### Characters Used
- **Double box**: `╔═╗║╚╝` for section headers
- **Single box**: `┏━┓┃┗━┛` for footer
- **Tree structure**: `├─└─` for nested items
- **Progress bars**: `[████░░░░░░]` for visual metrics
- **Confidence**: `●●●○○` for decision confidence

### Color Coding
- **Green** `\033[92m`: Active, positive, growing
- **Yellow** `\033[93m`: Stopped, medium, stable
- **Red** `\033[91m`: Idle, low, declining
- **Cyan** `\033[96m`: System-level info
- **Gray** `\033[90m`: Secondary info, explanations

---

## 🌟 Success Metrics

The Power Station is successful when you see:

1. **Energy Growth > 0%** (system generating more energy than baseline)
2. **Queen ACTIVE** (💚 heartbeat shows recent decisions)
3. **High Mobility** (>50% idle energy ready to redistribute)
4. **Positive Net Flow** (24h energy gain > 0)
5. **High Efficiency** (>70% of moves result in net gain)

---

## 🚦 Status Indicators Quick Reference

| Icon | Meaning |
|------|---------|
| 💚 ACTIVE | Queen engine running, making decisions |
| 💔 IDLE | Queen engine stopped or no opportunities |
| 🟢 RUNNING | Power station operational |
| 🟡 STOPPED | Power station idle |
| 🟢 HIGH | >50% energy available (good mobility) |
| 🟡 MED | 10-50% energy available |
| 🔴 LOW | <10% energy available (mostly locked) |
| ✅ EXECUTE | Queen approved energy redistribution |
| 🚫 BLOCK | Queen prevented energy drain |
| ⚡📈 | Energy growing (positive) |
| ⚠️📉 | Energy declining (negative) |
| ⚡━ | Energy stable (neutral) |

---

## 📚 Related Documentation

- **[QUEEN_AUTONOMOUS_POWER_SYSTEM.md](./QUEEN_AUTONOMOUS_POWER_SYSTEM.md)** - Queen's decision-making system
- **[DIGITAL_OCEAN_DEPLOY.md](./DIGITAL_OCEAN_DEPLOY.md)** - Deployment guide
- **[.github/copilot-instructions.md](./.github/copilot-instructions.md)** - Full system architecture

---

**⚡ Welcome to the Aureon Power Station - Where Everything is Energy ⚡**
