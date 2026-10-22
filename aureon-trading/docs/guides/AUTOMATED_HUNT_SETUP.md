# 🦁 Automated Hunt Loop Setup

The Automated Hunt Loop continuously scans crypto markets, identifies high-opportunity targets, generates QGITA signals, and routes orders through the OMS queue—fully autonomous.

## ✅ What's Deployed

- **Database Tables**: `hunt_sessions`, `hunt_targets`, `hunt_scans`
- **Edge Function**: `automated-hunt-loop` (Pride Scanner + Signal Router)
- **UI Component**: `AutomatedHuntControl` in Markets tab
- **Hook**: `useAutomatedHunt` for session management

## 🎯 How It Works

```
1. PRIDE SCANNER → Fetch all USDT pairs from Binance
2. FILTER → Volatility ≥ 2%, Volume ≥ $100K
3. RANK → Score = volatility × volume
4. SELECT → Top 5 targets
5. QGITA → Generate signals (Tier 1/2/3 based on confidence)
6. OMS → Queue Tier 1 & 2 orders with priority
7. REPEAT → Every 5 minutes (configurable)
```

## 🚀 Quick Start

### 1. Start Required Services

Before starting the hunt, ensure:

```bash
# 1. Start Queen-Hive session (in Markets → Hive tab)
#    - Set initial capital (e.g., $100)
#    - Click "Deploy Queen-Hive"

# 2. Verify OMS is running
#    - Check Markets → Hive tab → OMS Queue Monitor
#    - Should show "Ready" status
```

### 2. Start the Hunt (UI)

Navigate to **Markets → 🦁 Hunt tab**:

1. Configure settings:
   - **Min Volatility**: 2.0% (default) - Lower to find more targets
   - **Min Volume**: $100,000 (default) - Raise for liquid markets only
   - **Max Targets**: 5 (default) - How many top opportunities to process
   - **Scan Interval**: 300s (5 min) - How often to scan

2. Click **"Start Hunt"**

3. Monitor:
   - **Scans**: Total number of hunt cycles
   - **Targets**: Total opportunities discovered
   - **Signals**: QGITA signals generated
   - **Queued**: Orders successfully queued in OMS

### 3. Manual Scan Trigger

While hunt is active, you can trigger immediate scans:

```bash
# Click "Scan Now" button in UI
# Or wait for automatic scan at configured interval
```

## 📊 What Gets Queued

Only **Tier 1** and **Tier 2** QGITA signals are queued:

| Tier | Confidence | Priority | Position Size |
|------|-----------|----------|---------------|
| **Tier 1** | 80-100% | P80-100 | 100% ($100 default) |
| **Tier 2** | 60-79% | P60-79 | 50% ($50 default) |
| Tier 3 | <60% | - | Rejected (not queued) |

**Priority Bonuses:**
- High volatility (>10%): +10
- High volume (>$10M): +5

## 🔄 Optional: Fully Automated Cron (Advanced)

To run hunts automatically even when browser is closed, set up a cron job:

### Enable Required Extensions

First, enable `pg_cron` and `pg_net` extensions in your Supabase project:

1. Go to Lovable Cloud → Database → Extensions
2. Enable `pg_cron`
3. Enable `pg_net`

### Create Cron Job

**IMPORTANT**: Replace `YOUR_PROJECT_ID` and `YOUR_ANON_KEY` with your actual values:

- Project ID: Found in Lovable Cloud → Settings
- Anon Key: Found in Lovable Cloud → Settings → API

```sql
-- Run hunt scan every 5 minutes
SELECT cron.schedule(
  'automated-hunt-loop-every-5min',
  '*/5 * * * *',  -- Every 5 minutes
  $$
  SELECT
    net.http_post(
        url:='https://YOUR_PROJECT_ID.supabase.co/functions/v1/automated-hunt-loop',
        headers:='{"Content-Type": "application/json", "Authorization": "Bearer YOUR_ANON_KEY"}'::jsonb,
        body:='{"action": "scan", "huntSessionId": "YOUR_HUNT_SESSION_ID"}'::jsonb
    ) as request_id;
  $$
);
```

**To get your Hunt Session ID:**
1. Start a hunt via UI
2. Open browser console
3. Run: `localStorage.getItem('hunt-session-id')`
4. Copy the ID and paste it into the cron job SQL above

**To stop the cron:**
```sql
SELECT cron.unschedule('automated-hunt-loop-every-5min');
```

## 🛑 Stopping the Hunt

### Via UI
Click **"Stop Hunt"** button in Markets → 🦁 Hunt tab

### Via Cron (if enabled)
```sql
-- Unschedule the cron job
SELECT cron.unschedule('automated-hunt-loop-every-5min');
```

## 📈 Monitoring

### Real-Time Stats

In the UI, you'll see:
- **Total Scans**: How many pride scans completed
- **Targets Found**: Total high-opportunity symbols discovered
- **Signals Generated**: QGITA signals created
- **Orders Queued**: Orders successfully added to OMS

### Recent Targets

View the top 5 most recent targets with:
- Symbol name
- Opportunity score
- Volatility %
- Whether queued in OMS
- Signal tier

### Database Queries

```sql
-- View all hunt sessions
SELECT * FROM hunt_sessions ORDER BY started_at DESC;

-- View recent targets
SELECT symbol, opportunity_score, volatility_24h, signal_tier, order_queued
FROM hunt_targets
ORDER BY discovered_at DESC
LIMIT 20;

-- View scan history
SELECT scan_timestamp, pairs_scanned, targets_found, orders_queued, top_symbol
FROM hunt_scans
ORDER BY scan_timestamp DESC
LIMIT 10;
```

## 🎯 Performance Tuning

### Finding More Targets

If no targets found:
- **Lower min volatility** to 1.0% or 0.5%
- **Lower min volume** to $50,000 or $10,000
- **Increase max targets** to 10 or 20

### Conservative Trading

For safer operation:
- **Raise min volatility** to 5.0% or 10.0%
- **Raise min volume** to $1,000,000
- **Decrease max targets** to 3

### Scan Frequency

- **Aggressive**: 60s (1 minute) - High API usage
- **Balanced**: 300s (5 minutes) - Default
- **Conservative**: 600s (10 minutes) - Lower API usage

## 🔒 Safety Features

✅ **Only Tier 1 & 2 signals queued** (≥60% confidence)
✅ **OMS rate limiting** (100 orders/10s Binance limit)
✅ **Priority-based queue** (high-quality signals first)
✅ **Graceful error handling** (failed targets marked, hunt continues)
✅ **Circuit breaker** (stops if repeated failures)

## 🐛 Troubleshooting

### "No active hive found"
**Solution**: Start a Queen-Hive session first (Markets → Hive tab)

### "No targets found"
**Solution**: Lower volatility threshold or wait for volatile market conditions

### "Failed to queue order"
**Solution**: Check OMS Queue Monitor for rate limit status

### Cron not running
**Solution**: 
1. Verify extensions enabled: `SELECT * FROM pg_extension WHERE extname IN ('pg_cron', 'pg_net');`
2. Check cron jobs: `SELECT * FROM cron.job;`
3. Check logs: `SELECT * FROM cron.job_run_details ORDER BY start_time DESC LIMIT 10;`

## 📚 Related Documentation

- [Lion Hunt Flow](docs/LION_HUNT_FLOW.md) - CLI version architecture
- [QGITA Signals](src/core/qgitaSignalGenerator.ts) - Signal generation logic
- [OMS Queue](supabase/functions/oms-leaky-bucket/index.ts) - Rate limiting system
- [Queen-Hive](supabase/functions/queen-hive-orchestrator/index.ts) - Multi-agent system

## 🦁 Hunt Status

✅ **Pride Scanner**: Scans all USDT pairs on Binance
✅ **Opportunity Ranking**: Volatility × Volume scoring
✅ **QGITA Integration**: Automatic signal generation
✅ **OMS Routing**: Priority-based queue with rate limits
✅ **Auto-loop**: Configurable scan intervals
✅ **Web UI**: Full control panel in Markets tab

**The Lion is ready to hunt. Leave no stone unturned.** 🌈💎
