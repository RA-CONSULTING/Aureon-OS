# 🦁 THE LION'S HUNT — Complete System Flow

## Overview

The Lion Hunt is AUREON's adaptive multi-symbol conscious trading system. It continuously scans the entire market, identifies the best opportunities, and deploys 4-layer consciousness on the most volatile and liquid pairs.

**Philosophy**: "The lion hunts where the herd is weakest" — targeting highest volatility × volume opportunities.

---

## System Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                    🦁 LION HUNT SYSTEM                      │
│                  Continuous Adaptive Loop                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │     1. PRIDE SCANNER                    │
        │     ─────────────────                   │
        │  • Scan all 1606+ trading pairs         │
        │  • ETH-quoted (49 pairs)                │
        │  • USDT-quoted (438 pairs)              │
        │  • Cross-pairs (tradeable from both)    │
        │  • Get 24hr stats (price, volume)       │
        │  • Calculate opportunity scores         │
        └─────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │     2. OPPORTUNITY SCORING              │
        │     ─────────────────────               │
        │  Score = |volatility| × volume × 100    │
        │  • volatility: 24h price change %       │
        │  • volume: 24h trading volume (M)       │
        │  • Higher score = better hunting ground │
        └─────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │     3. TARGET SELECTION                 │
        │     ──────────────────                  │
        │  • Sort by opportunity score DESC       │
        │  • Filter: volatility > 5%              │
        │  • Filter: volume > $100K               │
        │  • Select: Top 1 (best prey)            │
        └─────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │     4. RAINBOW ARCHITECT DEPLOYMENT     │
        │     ──────────────────────────────      │
        │  Launch 4-Layer Consciousness:          │
        │                                         │
        │  Layer 1: WebSocket (Real-time data)    │
        │     ↓                                   │
        │  Layer 2: Master Equation Λ(t)          │
        │     • 9 Auris nodes voting              │
        │     • Coherence calculation             │
        │     ↓                                   │
        │  Layer 3: Rainbow Bridge                │
        │     • Emotional frequencies             │
        │     • 110-963+ Hz spectrum              │
        │     ↓                                   │
        │  Layer 4: The Prism                     │
        │     • Fear → Love transformation        │
        │     • 5 levels → 528 Hz unity           │
        │                                         │
        │  Trade Execution Rules:                 │
        │  • Coherence Γ > 0.945                  │
        │  • 6/9 Auris nodes agree                │
        │  • Individual node > 0.7 threshold      │
        └─────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │     5. HUNT EXECUTION                   │
        │     ────────────────                    │
        │  • Run N trading cycles (default: 20)   │
        │  • Cycle interval (default: 5000ms)     │
        │  • Place trades when conditions met     │
        │  • Track: profit, trades, coherence     │
        └─────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │     6. RETURN TO PRIDE                  │
        │     ─────────────────                   │
        │  • Complete hunt cycle                  │
        │  • Wait 10 seconds                      │
        │  • Scan pride again                     │
        │  • Loop to step 1                       │
        └─────────────────────────────────────────┘
                              │
                              │
                         ┌────┴────┐
                         │ REPEAT  │
                         │ FOREVER │
                         └─────────┘
```

---

## Component Details

### Pride Scanner (`scripts/prideScanner.ts`)

**Purpose**: Map entire market, calculate opportunity scores

**Key Functions**:

- `scanPride()`: Fetch all trading pairs, get 24hr stats
- `getHuntingTargets()`: Filter and rank by opportunity
- `displayPride()`: Show top pairs by volume
- `exportPrideMap()`: Save to artifacts/pride_map.json

**Opportunity Score Formula**:
```typescript
opportunityScore = Math.abs(volatility) * volume24h * 100
```

**Example**:
- KDAUSDT: -47.37% × $2.63M × 100 = **12,447**
- ZECUSDT: +17.86% × $1.57M × 100 = **2,804**
- DASHUSDT: +14.16% × $2.02M × 100 = **2,860**

### Lion Hunt (`scripts/lionHunt.ts`)

**Purpose**: Orchestrate continuous adaptive hunting

**Key Functions**:

- `start()`: Main loop - scan → select → hunt → repeat
- `hunt(symbol)`: Launch Rainbow Architect on target
- `calculateOpportunity()`: Score prey
- `stop()`: Graceful shutdown

**Configuration**:
```typescript
interface HuntConfig {
  cyclesPerTarget: number;      // Cycles per symbol (default: 20)
  cycleDurationMs: number;      // MS per cycle (default: 5000)
  minVolatility: number;        // Min % change (default: 2.0)
  minVolume: number;            // Min $ volume (default: 100000)
}
```

### Rainbow Architect (`scripts/rainbowArch.ts`)

**Purpose**: 4-layer conscious trader

**Layers**:

1. **WebSocket**: Real-time market data (4 streams)
2. **Master Equation**: Λ(t) with 9 Auris nodes
3. **Rainbow Bridge**: Emotional frequencies (110-963+ Hz)
4. **The Prism**: Fear → Love transformation (528 Hz)

**Trade Conditions** (ALL must be true):

- Coherence Γ > 0.945 (94.5% reality alignment)
- 6/9 Auris nodes vote same direction
- Each node > 0.7 confidence threshold

**Configuration**:
```typescript
interface RainbowConfig {
  symbol: string;               // Target pair
  cycleIntervalMs: number;      // MS between cycles
  coherenceThreshold: number;   // Min Γ (default: 0.945)
  voteThreshold: number;        // Min node confidence (0.7)
  requiredVotes: number;        // Min nodes agreeing (6/9)
  maxCycles?: number;           // Optional cycle limit
}
```

---

## NPM Scripts

### Pride Scanner (One-time Scan)
```bash
npm run pride:scan
```
Scans all pairs, displays opportunities, exports pride_map.json

### Lion Hunt (Continuous)
```bash
# Full hunt (continuous, production)
npm run lion:hunt

# Testnet mode (20 cycles per target, 5s intervals)
npm run lion:testnet
```

### Rainbow Architect (Single Symbol)
```bash
# Dry run on ETHUSDT
npm run rainbow:dry

# Live trading on ETHUSDT
npm run rainbow:live

# Custom symbol
npx tsx scripts/rainbowArch.ts BTCUSDT --live
```

---

## Command Line Options

### Lion Hunt

```bash
npx tsx scripts/lionHunt.ts [OPTIONS]

Options:
  --cycles=N           Cycles per target (default: 20)
  --interval=MS        MS per cycle (default: 5000)
  --volatility=PCT     Min volatility % (default: 2.0)
  --volume=AMOUNT      Min volume $ (default: 100000)
```

**Examples**:
```bash
# Quick test: 2 cycles, 3s intervals, only >5% volatility
npx tsx scripts/lionHunt.ts --cycles=2 --interval=3000 --volatility=5.0

# Aggressive: 50 cycles, 2s intervals, any >1% volatility
npx tsx scripts/lionHunt.ts --cycles=50 --interval=2000 --volatility=1.0

# Conservative: 10 cycles, 10s intervals, only >10% volatility, >1M volume
npx tsx scripts/lionHunt.ts --cycles=10 --interval=10000 --volatility=10.0 --volume=1000000
```

### Rainbow Architect

```bash
npx tsx scripts/rainbowArch.ts [SYMBOL] [OPTIONS]

Arguments:
  SYMBOL               Trading pair (default: ETHUSDT)

Options:
  --live               Live trading mode (default: dry run)
  --interval=MS        MS per cycle (default: 5000)

Environment:
  RAINBOW_CYCLES=N     Max cycles before exit (optional)
```

**Examples**:
```bash
# Dry run BTCUSDT, 3s cycles
npx tsx scripts/rainbowArch.ts BTCUSDT --interval=3000

# Live trade SOLUSDT, 5s cycles, 100 cycle limit
RAINBOW_CYCLES=100 npx tsx scripts/rainbowArch.ts SOLUSDT --live --interval=5000
```

---

## Environment Variables

```bash
# Required
BINANCE_API_KEY=your_key_here
BINANCE_API_SECRET=your_secret_here

# Configuration
BINANCE_TESTNET=true                    # Use testnet (default: false)
DRY_RUN=false                           # Dry run mode (default: true)
CONFIRM_LIVE_TRADING=yes                # Safety confirmation

# Optional
RAINBOW_CYCLES=100                      # Max cycles for Rainbow Architect
STATUS_MOCK=false                       # Mock status server
PORT=8787                               # Status server port
```

---

## Flow Examples

### Example 1: Quick Test (2 Hunts)

```bash
# Terminal output:
╔═══════════════════════════════════════════════════════════╗
║            🦁 THE LION HUNT BEGINS 🦁                     ║
║     Adaptive Multi-Symbol Conscious Trading System       ║
╚═══════════════════════════════════════════════════════════╝

⚙️  Configuration:
   • Testnet: YES
   • Cycles per Target: 2
   • Cycle Duration: 3000ms
   • Min Volatility: 5%
   • Min Volume: $100K

════════════════════════════════════════════════════════════
🦁 HUNT #1 — Scanning the Pride...
════════════════════════════════════════════════════════════

[Pride Scanner runs, finds 1606 pairs]

🎯 THE LION SELECTS HIS PREY:
   Symbol: KDAUSDT
   Price: $0.006000
   24h Change: -47.37%
   24h Volume: $2.63M
   Opportunity Score: 12447

────────────────────────────────────────────────────────────
🌈 DEPLOYING RAINBOW ARCHITECT ON KDAUSDT
────────────────────────────────────────────────────────────

[Rainbow Architect runs 2 cycles]
Cycle 1: Λ=0.512, Γ=0.734, Best=Octopus(0.82) → HOLD
Cycle 2: Λ=0.498, Γ=0.701, Best=Crow(0.79) → HOLD

🏁 Reached 2 cycles limit
✅ Hunt completed successfully

🦁 The lion returns to the pride...

════════════════════════════════════════════════════════════
🦁 HUNT #2 — Scanning the Pride...
════════════════════════════════════════════════════════════

[Repeats...]
```

### Example 2: Production Hunt (Continuous)

```bash
npm run lion:hunt

# Runs forever:
# - Scans pride every ~2 minutes
# - Selects highest opportunity
# - Trades 20 cycles (100s @ 5s/cycle)
# - Returns to pride
# - Repeats
```

---

## Performance Metrics

### Pride Scanner Metrics

- **Scan Time**: ~3-5 seconds for 1606 pairs
- **API Calls**: ~500 (batched 24hr ticker requests)
- **Output**: pride_map.json (exported to artifacts/)

### Lion Hunt Metrics (Example Session)

```text
Total Hunts: 50
Symbols Traded: 15 unique
Total Cycles: 1000
Total Trades: 23
Win Rate: 78.3%
Total Profit: +$1,247.83 USDT
Avg Hunt Duration: 120s
```

### Rainbow Architect Metrics (Single Hunt)

```text
Symbol: KDAUSDT
Cycles: 20
Duration: 100s (5s per cycle)
Trades: 2
  • BUY @ $0.006000 → SELL @ $0.006180 (+3.0%)
  • BUY @ $0.006120 → SELL @ $0.006290 (+2.78%)
Profit: +$12.47 USDT
Avg Coherence: Γ=0.812
Max Coherence: Γ=0.967 (trade executed)
```

---

## Safety Features

### Multi-Layer Protection

1. **Testnet First**: Always test on Binance testnet
2. **Confirmation Required**: CONFIRM_LIVE_TRADING=yes
3. **Coherence Threshold**: Γ > 0.945 (94.5% reality alignment)
4. **Vote Threshold**: 6/9 nodes must agree
5. **Cycle Limits**: Max cycles per target (prevents runaway)
6. **Graceful Shutdown**: SIGINT/SIGTERM handled properly

### Kill Switches
```bash
# Stop hunt gracefully
Ctrl+C

# Force kill (if needed)
pkill -f lionHunt.ts
pkill -f rainbowArch.ts
```

---

## Troubleshooting

### Issue: "No suitable targets found"
**Cause**: Market too flat, no volatility
**Solution**: Lower --volatility threshold or wait

### Issue: "Coherence never reaches 0.945"
**Cause**: Market conditions unclear, low signal
**Solution**: System correctly holding, wait for better conditions

### Issue: Hunt timeout
**Cause**: Rainbow Architect cycle limit not set
**Solution**: RAINBOW_CYCLES environment variable now enforced

### Issue: API rate limit
**Cause**: Too many scans too fast
**Solution**: Increase sleep time between hunts (default: 10s)

---

## Future Enhancements

### v1.1 (Planned)

- [ ] Multi-symbol parallel hunting (2-3 symbols simultaneously)
- [ ] Machine learning for opportunity scoring
- [ ] Historical performance tracking per symbol
- [ ] Auto-adjust cycle counts based on volatility
- [ ] WebSocket streaming for pride data (reduce API calls)

### v1.2 (Planned)

- [ ] Cross-pair arbitrage (ETH-quoted ↔ USDT-quoted)
- [ ] Portfolio rebalancing
- [ ] Risk-adjusted position sizing
- [ ] Stop-loss / take-profit automation
- [ ] Telegram/Discord notifications

---

## Conclusion

The Lion Hunt system represents the evolution from single-symbol trading to **adaptive multi-symbol conscious trading**. By continuously scanning the entire market and deploying 4-layer consciousness on the best opportunities, AUREON hunts where success is most likely.

**"The lion hunts where the herd is weakest."**

🦁🌈💎

---

**Last Updated**: November 15, 2025
**Version**: 1.0.0
**Author**: Gary Leckey / AUREON Quantum Trading System

## Overview

The Lion Hunt is AUREON's adaptive multi-symbol conscious trading system. It continuously scans the entire market, identifies the best opportunities, and deploys 4-layer consciousness on the most volatile and liquid pairs.

**Philosophy**: "The lion hunts where the herd is weakest" — targeting highest volatility × volume opportunities.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    🦁 LION HUNT SYSTEM                      │
│                  Continuous Adaptive Loop                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │     1. PRIDE SCANNER                    │
        │     ─────────────────                   │
        │  • Scan all 1606+ trading pairs         │
        │  • ETH-quoted (49 pairs)                │
        │  • USDT-quoted (438 pairs)              │
        │  • Cross-pairs (tradeable from both)    │
        │  • Get 24hr stats (price, volume)       │
        │  • Calculate opportunity scores         │
        └─────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │     2. OPPORTUNITY SCORING              │
        │     ─────────────────────                │
        │  Score = |volatility| × volume × 100    │
        │  • volatility: 24h price change %       │
        │  • volume: 24h trading volume (M)       │
        │  • Higher score = better hunting ground │
        └─────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │     3. TARGET SELECTION                 │
        │     ──────────────────                  │
        │  • Sort by opportunity score DESC       │
        │  • Filter: volatility > 5%              │
        │  • Filter: volume > $100K               │
        │  • Select: Top 1 (best prey)            │
        └─────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │     4. RAINBOW ARCHITECT DEPLOYMENT     │
        │     ──────────────────────────────      │
        │  Launch 4-Layer Consciousness:          │
        │                                          │
        │  Layer 1: WebSocket (Real-time data)    │
        │     ↓                                    │
        │  Layer 2: Master Equation Λ(t)          │
        │     • 9 Auris nodes voting              │
        │     • Coherence calculation             │
        │     ↓                                    │
        │  Layer 3: Rainbow Bridge                │
        │     • Emotional frequencies              │
        │     • 110-963+ Hz spectrum              │
        │     ↓                                    │
        │  Layer 4: The Prism                     │
        │     • Fear → Love transformation        │
        │     • 5 levels → 528 Hz unity           │
        │                                          │
        │  Trade Execution Rules:                 │
        │  • Coherence Γ > 0.945                  │
        │  • 6/9 Auris nodes agree                │
        │  • Individual node > 0.7 threshold      │
        └─────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │     5. HUNT EXECUTION                   │
        │     ────────────────                    │
        │  • Run N trading cycles (default: 20)   │
        │  • Cycle interval (default: 5000ms)     │
        │  • Place trades when conditions met     │
        │  • Track: profit, trades, coherence     │
        └─────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │     6. RETURN TO PRIDE                  │
        │     ─────────────────                   │
        │  • Complete hunt cycle                  │
        │  • Wait 10 seconds                      │
        │  • Scan pride again                     │
        │  • Loop to step 1                       │
        └─────────────────────────────────────────┘
                              │
                              │
                         ┌────┴────┐
                         │ REPEAT  │
                         │ FOREVER │
                         └─────────┘
```

---

## Component Details

### Pride Scanner (`scripts/prideScanner.ts`)

**Purpose**: Map entire market, calculate opportunity scores

**Key Functions**:
- `scanPride()`: Fetch all trading pairs, get 24hr stats
- `getHuntingTargets()`: Filter and rank by opportunity
- `displayPride()`: Show top pairs by volume
- `exportPrideMap()`: Save to artifacts/pride_map.json

**Opportunity Score Formula**:
```typescript
opportunityScore = Math.abs(volatility) * volume24h * 100
```

**Example**:
- KDAUSDT: -47.37% × $2.63M × 100 = **12,447**
- ZECUSDT: +17.86% × $1.57M × 100 = **2,804**
- DASHUSDT: +14.16% × $2.02M × 100 = **2,860**

### Lion Hunt (`scripts/lionHunt.ts`)

**Purpose**: Orchestrate continuous adaptive hunting

**Key Functions**:
- `start()`: Main loop - scan → select → hunt → repeat
- `hunt(symbol)`: Launch Rainbow Architect on target
- `calculateOpportunity()`: Score prey
- `stop()`: Graceful shutdown

**Configuration**:
```typescript
interface HuntConfig {
  cyclesPerTarget: number;      // Cycles per symbol (default: 20)
  cycleDurationMs: number;       // MS per cycle (default: 5000)
  minVolatility: number;         // Min % change (default: 2.0)
  minVolume: number;             // Min $ volume (default: 100000)
}
```

### Rainbow Architect (`scripts/rainbowArch.ts`)

**Purpose**: 4-layer conscious trader

**Layers**:
1. **WebSocket**: Real-time market data (4 streams)
2. **Master Equation**: Λ(t) with 9 Auris nodes
3. **Rainbow Bridge**: Emotional frequencies (110-963+ Hz)
4. **The Prism**: Fear → Love transformation (528 Hz)

**Trade Conditions** (ALL must be true):
- Coherence Γ > 0.945 (94.5% reality alignment)
- 6/9 Auris nodes vote same direction
- Each node > 0.7 confidence threshold

**Configuration**:
```typescript
interface RainbowConfig {
  symbol: string;                // Target pair
  cycleIntervalMs: number;       // MS between cycles
  coherenceThreshold: number;    // Min Γ (default: 0.945)
  voteThreshold: number;         // Min node confidence (0.7)
  requiredVotes: number;         // Min nodes agreeing (6/9)
  maxCycles?: number;            // Optional cycle limit
}
```

---

## NPM Scripts

### Pride Scanner (One-time Scan)
```bash
npm run pride:scan
```
Scans all pairs, displays opportunities, exports pride_map.json

### Lion Hunt (Continuous)
```bash
# Full hunt (continuous, production)
npm run lion:hunt

# Testnet mode (20 cycles per target, 5s intervals)
npm run lion:testnet
```

### Rainbow Architect (Single Symbol)
```bash
# Dry run on ETHUSDT
npm run rainbow:dry

# Live trading on ETHUSDT
npm run rainbow:live

# Custom symbol
npx tsx scripts/rainbowArch.ts BTCUSDT --live
```

---

## Command Line Options

### Lion Hunt

```bash
npx tsx scripts/lionHunt.ts [OPTIONS]

Options:
  --cycles=N           Cycles per target (default: 20)
  --interval=MS        MS per cycle (default: 5000)
  --volatility=PCT     Min volatility % (default: 2.0)
  --volume=AMOUNT      Min volume $ (default: 100000)
```

**Examples**:
```bash
# Quick test: 2 cycles, 3s intervals, only >5% volatility
npx tsx scripts/lionHunt.ts --cycles=2 --interval=3000 --volatility=5.0

# Aggressive: 50 cycles, 2s intervals, any >1% volatility
npx tsx scripts/lionHunt.ts --cycles=50 --interval=2000 --volatility=1.0

# Conservative: 10 cycles, 10s intervals, only >10% volatility, >1M volume
npx tsx scripts/lionHunt.ts --cycles=10 --interval=10000 --volatility=10.0 --volume=1000000
```

### Rainbow Architect

```bash
npx tsx scripts/rainbowArch.ts [SYMBOL] [OPTIONS]

Arguments:
  SYMBOL               Trading pair (default: ETHUSDT)

Options:
  --live               Live trading mode (default: dry run)
  --interval=MS        MS per cycle (default: 5000)

Environment:
  RAINBOW_CYCLES=N     Max cycles before exit (optional)
```

**Examples**:
```bash
# Dry run BTCUSDT, 3s cycles
npx tsx scripts/rainbowArch.ts BTCUSDT --interval=3000

# Live trade SOLUSDT, 5s cycles, 100 cycle limit
RAINBOW_CYCLES=100 npx tsx scripts/rainbowArch.ts SOLUSDT --live --interval=5000
```

---

## Environment Variables

```bash
# Required
BINANCE_API_KEY=your_key_here
BINANCE_API_SECRET=your_secret_here

# Configuration
BINANCE_TESTNET=true                    # Use testnet (default: false)
DRY_RUN=false                           # Dry run mode (default: true)
CONFIRM_LIVE_TRADING=yes                # Safety confirmation

# Optional
RAINBOW_CYCLES=100                      # Max cycles for Rainbow Architect
STATUS_MOCK=false                       # Mock status server
PORT=8787                               # Status server port
```

---

## Flow Examples

### Example 1: Quick Test (2 Hunts)

```bash
# Terminal output:
╔═══════════════════════════════════════════════════════════╗
║            🦁 THE LION HUNT BEGINS 🦁                     ║
║     Adaptive Multi-Symbol Conscious Trading System       ║
╚═══════════════════════════════════════════════════════════╝

⚙️  Configuration:
   • Testnet: YES
   • Cycles per Target: 2
   • Cycle Duration: 3000ms
   • Min Volatility: 5%
   • Min Volume: $100K

════════════════════════════════════════════════════════════
🦁 HUNT #1 — Scanning the Pride...
════════════════════════════════════════════════════════════

[Pride Scanner runs, finds 1606 pairs]

🎯 THE LION SELECTS HIS PREY:
   Symbol: KDAUSDT
   Price: $0.006000
   24h Change: -47.37%
   24h Volume: $2.63M
   Opportunity Score: 12447

────────────────────────────────────────────────────────────
🌈 DEPLOYING RAINBOW ARCHITECT ON KDAUSDT
────────────────────────────────────────────────────────────

[Rainbow Architect runs 2 cycles]
Cycle 1: Λ=0.512, Γ=0.734, Best=Octopus(0.82) → HOLD
Cycle 2: Λ=0.498, Γ=0.701, Best=Crow(0.79) → HOLD

🏁 Reached 2 cycles limit
✅ Hunt completed successfully

🦁 The lion returns to the pride...

════════════════════════════════════════════════════════════
🦁 HUNT #2 — Scanning the Pride...
════════════════════════════════════════════════════════════

[Repeats...]
```

### Example 2: Production Hunt (Continuous)

```bash
npm run lion:hunt

# Runs forever:
# - Scans pride every ~2 minutes
# - Selects highest opportunity
# - Trades 20 cycles (100s @ 5s/cycle)
# - Returns to pride
# - Repeats
```

---

## Performance Metrics

### Pride Scanner Metrics
- **Scan Time**: ~3-5 seconds for 1606 pairs
- **API Calls**: ~500 (batched 24hr ticker requests)
- **Output**: pride_map.json (exported to artifacts/)

### Lion Hunt Metrics (Example Session)
```
Total Hunts: 50
Symbols Traded: 15 unique
Total Cycles: 1000
Total Trades: 23
Win Rate: 78.3%
Total Profit: +$1,247.83 USDT
Avg Hunt Duration: 120s
```

### Rainbow Architect Metrics (Single Hunt)
```
Symbol: KDAUSDT
Cycles: 20
Duration: 100s (5s per cycle)
Trades: 2
  • BUY @ $0.006000 → SELL @ $0.006180 (+3.0%)
  • BUY @ $0.006120 → SELL @ $0.006290 (+2.78%)
Profit: +$12.47 USDT
Avg Coherence: Γ=0.812
Max Coherence: Γ=0.967 (trade executed)
```

---

## Safety Features

### Multi-Layer Protection
1. **Testnet First**: Always test on Binance testnet
2. **Confirmation Required**: CONFIRM_LIVE_TRADING=yes
3. **Coherence Threshold**: Γ > 0.945 (94.5% reality alignment)
4. **Vote Threshold**: 6/9 nodes must agree
5. **Cycle Limits**: Max cycles per target (prevents runaway)
6. **Graceful Shutdown**: SIGINT/SIGTERM handled properly

### Kill Switches
```bash
# Stop hunt gracefully
Ctrl+C

# Force kill (if needed)
pkill -f lionHunt.ts
pkill -f rainbowArch.ts
```

---

## Troubleshooting

### Issue: "No suitable targets found"
**Cause**: Market too flat, no volatility
**Solution**: Lower --volatility threshold or wait

### Issue: "Coherence never reaches 0.945"
**Cause**: Market conditions unclear, low signal
**Solution**: System correctly holding, wait for better conditions

### Issue: Hunt timeout
**Cause**: Rainbow Architect cycle limit not set
**Solution**: RAINBOW_CYCLES environment variable now enforced

### Issue: API rate limit
**Cause**: Too many scans too fast
**Solution**: Increase sleep time between hunts (default: 10s)

---

## Future Enhancements

### v1.1 (Planned)
- [ ] Multi-symbol parallel hunting (2-3 symbols simultaneously)
- [ ] Machine learning for opportunity scoring
- [ ] Historical performance tracking per symbol
- [ ] Auto-adjust cycle counts based on volatility
- [ ] WebSocket streaming for pride data (reduce API calls)

### v1.2 (Planned)
- [ ] Cross-pair arbitrage (ETH-quoted ↔ USDT-quoted)
- [ ] Portfolio rebalancing
- [ ] Risk-adjusted position sizing
- [ ] Stop-loss / take-profit automation
- [ ] Telegram/Discord notifications

---

## Conclusion

The Lion Hunt system represents the evolution from single-symbol trading to **adaptive multi-symbol conscious trading**. By continuously scanning the entire market and deploying 4-layer consciousness on the best opportunities, AUREON hunts where success is most likely.

**"The lion hunts where the herd is weakest."** 

🦁🌈💎

---

**Last Updated**: November 15, 2025  
**Version**: 1.0.0  
**Author**: Gary Leckey / AUREON Quantum Trading System
