# 🌈 Rainbow Architect - Quick Start

## What Is This?

AUREON now **tastes the market rainbow** through real-time Binance WebSocket streams!

Instead of polling price once per cycle, the system now receives:
- **@aggTrade** - Real-time trades (price + momentum)
- **@depth@100ms** - Order book updates (bid/ask/spread) 
- **@miniTicker** - 24hr statistics (volume/volatility baseline)
- **@kline_1m** - Candlestick patterns (trend detection)

The 9 Auris nodes now respond to:
- **Price** (as before)
- **Volatility** (calculated from 100-trade buffer)
- **Momentum** (% price change)
- **Spread** (bid-ask spread from order book)
- **Volume** (trading activity)

## Quick Test

```bash
npm run rainbow:dry
```

**What happens:**
1. Connects to live Binance WebSocket
2. Subscribes to 4 ETHUSDT streams
3. Accumulates 5 seconds of market data
4. Runs trading cycles every 5 seconds
5. Displays rich market snapshot + Λ(t) state
6. Shows 9-node Lighthouse voting
7. **DRY RUN** - no real trades

## Example Output

```
📊 Market: ETHUSDT
   Price: $3176.77
   Spread: $0.01
   Volatility: 0.00%
   Momentum: 0.00%

🌊 Master Equation Λ(t):
   Λ(t): -1.655905
   Γ:    0.509 (50.9% coherence)

🔦 Lighthouse Consensus: SELL
   ✓ Owl           80%
   ✓ Deer         100%
   ✓ Dolphin       91%
   ✗ Tiger         16%
   ✓ Hummingbird   76%
   ✓ CargoShip     72%
   ✓ Clownfish     70%
   ✓ Falcon        87%
   ✓ Panda         99%
   Votes: 8/9
   Signal: HOLD (need Γ>0.945)
```

## Key Improvements

| Feature | Co-Architect (Before) | Rainbow (Now) |
|---------|---------------------|---------------|
| Data Source | REST API | WebSocket |
| Latency | 200-500ms | 50-1000ms |
| Market Info | Price only | Price + volatility + momentum + spread + volume |
| Updates | Poll every 5s | Push (real-time events) |
| Node Response | Price velocity | Multi-factor (6 dimensions) |

## Node Personalities Enhanced

Each of the 9 Auris nodes now has unique market sensitivity:

- **Tiger** - Amplifies volatility + spread (disruptor)
- **Falcon** - Tracks momentum + volume (velocity)
- **Hummingbird** - Dampens turbulence + prefers tight spreads (stabilizer)
- **Dolphin** - Oscillates with momentum phase (emotion)
- **Deer** - Subtle sensitivity to all factors (sensing)
- **Owl** - Inverts on momentum reversals (memory)
- **Panda** - Resonates with stable high-volume (love)
- **CargoShip** - Responds to large volume (infrastructure)
- **Clownfish** - Detects micro-changes (symbiosis)

## Configuration

In `scripts/rainbowArch.ts`:

```typescript
const DEFAULT_RAINBOW_CONFIG = {
  symbol: 'ETHUSDT',
  cycleIntervalMs: 5000,       // 5 seconds
  coherenceThreshold: 0.945,   // 94.5% field coherence
  voteThreshold: 0.7,          // 70% resonance for vote
  requiredVotes: 6,            // 6/9 nodes must agree
  dryRun: true,
  positionSizePercent: 2,      // 2% per trade
};
```

## Live Trading (⚠️ DANGER)

```bash
npm run rainbow:live
```

Executes real market orders with real money!

## Safety Features

- Default: `dryRun: true`
- WebSocket auto-reconnect (max 10 attempts)
- Heartbeat monitoring (20s pings)
- Rate limiting (5 messages/second)
- Balance validation before orders
- Graceful shutdown (Ctrl+C)

## Documentation

Full docs: `docs/RAINBOW_ARCHITECT.md`

---

**🌈 Let the 9 nodes taste the rainbow!**
