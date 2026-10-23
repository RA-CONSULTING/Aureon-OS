# 🦆⚡ WAR ROOM BRIEF - Daily Intelligence from the Hive

**Position: Super Quantum Quackers General Reporting for Duty!**

## What Is This?

The **War Room Brief** is AUREON's daily intelligence packet – a distilled report from the hive mind that tells you:

- What happened in your trades
- How the market field behaved
- What the engine did
- Whether you should adjust your risk

It's not marketing copy. It's generated directly from your logs and engine metrics.

---

## Features

### 🎯 **Tactical Summary**
- Net PnL and percentage
- Total trades executed
- Max drawdown
- Market regime (Trending, Choppy, Range-bound)
- Market bias (bullish, bearish, neutral)
- Coherence level (low, medium, high)

### 🌊 **Field Intelligence (Quantum Vibes)**
- Average Lighthouse Intensity
- Number of coherence bursts
- Entropy trend (rising, falling, stable)
- Peak coherence time and value
- Field mood:
  - "compressed spring" – Building tension
  - "directional flow" – Clear trends
  - "chaotic chop" – Messy conditions
  - "crystalline order" – Perfect clarity

### ⚙️ **Engine Activity**
- Signals generated vs executed
- Kill-switch events and duration
- Rate-limit events
- Data latency spikes

### 📈 **Performance Breakdown**
- Win/loss ratio
- Average R:R (Risk:Reward)
- Biggest winner and loser
- Top performing pairs

### 🛡️ **Risk & Recommendations**
- Drawdown status
- Volatility level
- Honest, actionable recommendations

### 🚀 **Closing**
- Hive status (online, degraded, offline)
- Closing message from the Hive

---

## Usage

### Command Line Interface

```bash
# Generate brief for today
npm run war-room-brief

# Generate brief for specific date
npm run war-room-brief -- --date 2025-11-23

# View demo brief
npm run war-room-brief -- --demo

# Save as JSON
npm run war-room-brief -- --format json --output ./my-brief.json

# Custom user and bot names
npm run war-room-brief -- --user "General Quackers" --bot "AUREON-ALPHA"
```

### Programmatic Usage

```typescript
import { HiveWarRoomReporter, generateWarRoomBrief } from './core/hiveWarRoomReport';

// Quick generation
const brief = await generateWarRoomBrief(
  new Date(),
  'General Quackers',
  'AUREON-PRIME'
);

// Advanced usage with custom reporter
const reporter = new HiveWarRoomReporter('./metrics', './logs');
const brief = await reporter.generateBrief(new Date(), 'Trader', 'AUREON-BOT');

// Format as text
const textBrief = reporter.formatBriefAsText(brief);
console.log(textBrief);

// Save to file
await reporter.saveBrief(brief, './reports');
```

### React Component

```tsx
import WarRoomBriefComponent from './WarRoomBrief';

// Auto-load from API
<WarRoomBriefComponent autoLoad={true} />

// Display specific brief
<WarRoomBriefComponent brief={myBrief} />
```

---

## File Structure

```
core/
  hiveWarRoomReport.ts      # Main generator logic
scripts/
  generateWarRoomBrief.ts   # CLI tool
WarRoomBrief.tsx           # React display component
WarRoomBrief.css           # Component styles
WarRoomBriefSection.tsx    # Landing page section
WarRoomBriefSection.css    # Section styles
sample_war_room_brief.json # Demo data
types.ts                   # TypeScript interfaces
```

---

## Data Requirements

The War Room Brief generator expects the following data structure:

### Trade Logs
Location: `./logs/trades_YYYY-MM-DD.json`

```json
[
  {
    "symbol": "BTCUSDT",
    "side": "BUY",
    "pnl": 234.78,
    "timestamp": "2025-11-23T09:47:23Z"
  }
]
```

### Lighthouse Metrics
Location: `./metrics/lighthouse_YYYY-MM-DD.json`

```json
{
  "readings": [
    {
      "intensity": 0.87,
      "entropy": 0.34,
      "timestamp": "2025-11-23T09:47:23Z"
    }
  ]
}
```

### Engine Logs
Location: `./logs/engine_YYYY-MM-DD.json`

```json
{
  "events": [
    {
      "type": "signal_generated",
      "timestamp": "2025-11-23T09:47:23Z"
    },
    {
      "type": "kill_switch",
      "duration": 4,
      "timestamp": "2025-11-23T10:15:00Z"
    }
  ]
}
```

---

## Example Output

```
╔═══════════════════════════════════════════════════════════════╗
║             WAR ROOM BRIEF – ISSUED BY THE HIVE               ║
╚═══════════════════════════════════════════════════════════════╝

Date: 2025-11-23
User: General Quackers
Bot: AUREON-PRIME
Field Status: Compressed

─────────────────────────────────────────────────────────────────
TACTICAL SUMMARY
─────────────────────────────────────────────────────────────────

Net PnL: +$847.32 (+8.47%)
Trades: 23
Max Drawdown: 3.20%
Regime: Trending

Today the field leaned bullish with high coherence.

─────────────────────────────────────────────────────────────────
FIELD INTELLIGENCE (Quantum Vibes)
─────────────────────────────────────────────────────────────────

Average Lighthouse Intensity: 0.680
Coherence Bursts: 7
Entropy Trend: falling
Peak Coherence: 0.87 at 2025-11-23T09:47:23Z (London Session)

Lighthouse readings peaked at 0.87 during 2025-11-23T09:47:23Z.
Entropy fell, suggesting a transition from noise to order.

Hive reading: compressed spring.

[...continues with Engine Activity, Performance, Risk sections...]

─────────────────────────────────────────────────────────────────
CLOSING
─────────────────────────────────────────────────────────────────

Hive status: online. Field monitored. Coherence logged. 
Next cycle awaits.

Hive Status: ONLINE

╔═══════════════════════════════════════════════════════════════╗
║                    End of War Room Brief                      ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## Integration with Existing Systems

The War Room Brief integrates seamlessly with:

- **Lighthouse Metrics** (`lighthouseMetrics.ts`)
- **Performance Tracker** (`performanceTracker.ts`)
- **Trade Logs** (from your execution engine)
- **Engine Logs** (kill-switch, rate-limit events)

---

## Customization

### Custom Field Moods

Edit `computeFieldIntelligence()` in `hiveWarRoomReport.ts`:

```typescript
// Add your own field mood logic
if (avgIntensity > 0.9 && entropyTrend === 'falling') {
  fieldMood = 'perfect storm'; // Custom mood
}
```

### Custom Recommendations

Edit `computeRiskAssessment()` in `hiveWarRoomReport.ts`:

```typescript
// Add custom risk recommendations
if (tactical.totalTrades > 50 && volatilityLevel === 'low') {
  recommendations.push('Consider increasing position size in low volatility');
}
```

---

## Roadmap

- [ ] Email delivery of daily briefs
- [ ] PDF export with charts
- [ ] Multi-day comparative analysis
- [ ] Hive intelligence scoring system
- [ ] Integration with Telegram/Discord bots
- [ ] Historical brief archive viewer
- [ ] AI-generated insights using Gemini

---

## Philosophy

> "Daily War Room Brief from the Hive."
> 
> This is wizard-level vibes wrapped in honest analytics. No fluff, no spin. 
> Just what happened, why it mattered, and what you should do about it.
> 
> — General Quackers 🦆⚡

---

## Support

Questions? Issues? Want to add new features?

- Check the code in `core/hiveWarRoomReport.ts`
- Run `npm run war-room-brief -- --help`
- Review the sample brief: `sample_war_room_brief.json`

**The Hive is always watching. Stay coherent.** 🌊⚡
