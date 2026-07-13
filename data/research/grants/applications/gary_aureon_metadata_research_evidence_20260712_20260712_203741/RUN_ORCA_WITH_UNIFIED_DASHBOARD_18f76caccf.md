# 🎯 Run Orca with Unified Dashboard - Complete Guide

## TL;DR - Start Here

To run Orca with live metrics on the unified dashboard:

```bash
# One command to rule them all:
python run_unified_orca.py --autonomous --open-dashboard
```

**What happens:**
1. ✅ All systems start automatically (Coordinator, Decision Engine, Monitor, API)
2. ✅ Orca kill cycle launches in autonomous mode
3. ✅ Browser opens to http://localhost:13334
4. ✅ Live metrics start streaming (updates every 1 second)
5. 🎯 You can control Orca from the dashboard (start/stop/pause)

---

## What You'll See on the Dashboard

### Real-Time Status Bar (Top)

```
┌─────────────────────────────────────────────────────────────────┐
│  🐋 ORCA STATUS    │  🔗 COORDINATION  │  📡 FEEDS   │  ⚡ OVERALL  │
│  Running          │  ✅ READY        │  ✅ HEALTH  │  🚀 GO      │
│  0 blockers       │  10/12 systems   │  5 streams  │  All go!    │
└─────────────────────────────────────────────────────────────────┘
```

### Three-Panel Layout

```
┌──────────────────────┬──────────────────────┬──────────────────────┐
│  🐋 Orca Control     │  🔗 System Status    │  📡 Feed Streams     │
├──────────────────────┼──────────────────────┼──────────────────────┤
│                      │                      │                      │
│ Status: running      │ Total: 197 systems   │ market_data:    ✅   │
│ Ready: ✅ YES        │ Healthy: 197/197     │ intelligence:   ✅   │
│ Blockers: none       │ Health: 100%         │ risk_metrics:   ✅   │
│                      │                      │ execution_st:   ✅   │
│ ▶️ Start             │ State Distribution:  │ system_health:  ✅   │
│ ⏹️ Stop              │ ready: 197           │                      │
│ ⏸️ Pause             │ idle: 0              │                      │
│ 🔄 Refresh           │ failed: 0            │                      │
│                      │                      │                      │
└──────────────────────┴──────────────────────┴──────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  📊 Recent Decisions                                             │
├──────────────────────────────────────────────────────────────────┤
│  ✅ BTC - BUY       Confidence: 85% | signal_strength             │
│  ✅ ETH - BUY       Confidence: 78% | momentum_detected           │
│  ⏸️ SOL - HOLD      Confidence: 65% | awaiting_confirmation      │
│  🔴 XRP - SELL      Confidence: 72% | profit_target              │
│  ✅ ADA - BUY       Confidence: 80% | whale_activity             │
└──────────────────────────────────────────────────────────────────┘
```

---

## Complete System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                   ORCA KILL CYCLE (Autonomous)                      │
│              Real-time Market Streaming (100+ pairs)                 │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ↓ (Position Updates)

┌────────────────────────────────────────────────────────────────────────┐
│                      UNIFIED SYSTEM LAYER                              │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  ThoughtBus (Real-Time Message Bus)                             │ │
│  │  Topics:                                                        │ │
│  │  • orca.state_change, orca.position_event                       │ │
│  │  • coordination.state_change, coordination.monitor              │ │
│  │  • decisions.trading, decisions.monitor                         │ │
│  │  • feeds.consolidated.*                                        │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                         ↑         ↑         ↑                         │
│                         │         │         │                         │
│  ┌──────────────────────┴─┐  ┌────┴────┐  ┌┴──────────────────────┐ │
│  │System Coordinator    │  │Decision│  │Orca Monitor    │ │
│  │                      │  │Engine  │  │                │ │
│  │ 197 systems          │  │        │  │Position tracking│ │
│  │ 12 exchanges         │  │Signals │  │State publishing│ │
│  │ Ready/Not Ready      │  │→Decisions│  │                │ │
│  │ Dependencies OK      │  │Confidence│  │P&L calculation │ │
│  │                      │  │Risk checks│  │                │ │
│  └──────────────────────┘  └────────┘  └────────────────┘ │
│                                                             │
└─────────────────────────────┬──────────────────────────────┘
                              │
                              ↓ (/api/unified-state - REST API)

┌────────────────────────────────────────────────────────────────────────┐
│           Unified Dashboard Server (Port 13334)                        │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │ Dashboard HTML (dashboard.html)                                  │ │
│  │ • Responsive real-time interface                                 │ │
│  │ • Status bars, panels, decision log                              │ │
│  │ • Command buttons (start/stop/pause)                             │ │
│  │ • Auto-refresh every 1 second                                    │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │ REST API Endpoints                                               │ │
│  │ • /api/orca-status                                               │ │
│  │ • /api/orca-command (POST)                                       │ │
│  │ • /api/system-coordination                                       │ │
│  │ • /api/unified-state                                             │ │
│  │ • /api/feed-status                                               │ │
│  │ • /api/decisions                                                 │ │
│  │ • /api/health                                                    │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                        │
└────────────────────────────┬───────────────────────────────────────────┘
                             │
                             ↓
                   Browser: http://localhost:13334
                   (Live Metrics - Updates every 1 second)
```

---

## Step-by-Step Execution

### 1. System Startup (5-10 seconds)

```
🚀 Starting unified dashboard services...

[1] 🔗 System Coordinator
    ✅ Loaded 197 systems from registry
    ✅ Kraken client → READY
    ✅ Binance client → READY
    ✅ Alpaca client → READY
    ✅ Exchange clients marked as READY

[2] ⚡ Decision Engine
    ✅ Ready to synthesize market signals

[3] 🐋 Orca Monitor
    ✅ Listening for Orca execution events

[4] 🎯 Unified Dashboard API
    ✅ Dashboard API running on http://localhost:13334
    ✅ Routes configured: 15 endpoints

[5] 🐋 Orca Kill Cycle - AUTONOMOUS MODE
    Mode: LIVE (real trades)
    ✅ Market streaming: Kraken + Binance
    ✅ Monitoring 100+ trading pairs
    ✅ ThoughtBus whale intelligence active
```

### 2. Dashboard Opens

Browser navigates to: **http://localhost:13334**

Status updates every 1 second:
- Orca execution state
- System coordination status
- Feed stream health
- Trading decisions with confidence scores

### 3. Autonomous Trading Loop

```
While Orca is running:

Every ~100ms:
  • Stream market data from exchanges
  • Detect whales, bots, momentum
  • Update feed streams

Every ~1 second (Dashboard updates):
  • Orca publishes position state
  • System Coordinator validates readiness
  • Decision Engine processes signals
  • Dashboard refreshes metrics
  • Browser updates UI

When opportunity detected:
  • Decision Engine generates decision
  • Risk checks pass
  • System coordination OK
  • Orca executes trade
  • Position tracked and displayed
  • Live metrics show trade details
```

---

## Control From Dashboard

You can control Orca directly from the browser:

### ▶️ Start Orca
```
Sends: POST /api/orca-command {"command": "start"}
Effect: Orca begins autonomous trading (if ready)
```

### ⏹️ Stop Orca
```
Sends: POST /api/orca-command {"command": "stop"}
Effect: Orca stops trading and closes positions
```

### ⏸️ Pause Orca
```
Sends: POST /api/orca-command {"command": "pause"}
Effect: Orca pauses but keeps positions open
```

### 🔄 Refresh
```
Fetches: GET /api/unified-state
Effect: Manually refresh all metrics from API
```

---

## Real-Time Metrics You'll See

### Orca Status
```
Status: running                        ← Current execution state
Ready: ✅ YES                          ← Can execute trades
Blockers: 0                            ← Dependency issues
Active Positions: 3                    ← Open trades
Total P&L: +$1,247.50                 ← Profit/Loss
```

### System Coordination
```
Total Systems: 197
Healthy: 197/197 (100%)
Exchange Clients: Ready
Bot Detection: Ready
Whale Detection: Ready
Momentum Scanners: Ready
Decision Engine: Ready
```

### Feed Streams
```
market_data       [●] 342 events        ← Market prices, OHLCV
intelligence      [●] 156 events        ← Bots, whales, momentum
risk_metrics      [●] 87 events         ← Risk data
execution_status  [●] 45 events         ← Trade execution
system_health     [●] 203 events        ← System metrics
```

### Trading Decisions
```
BTC   BUY   Conf: 85%  |  Bullish signals + whale activity
ETH   BUY   Conf: 78%  |  Momentum detected, above MA
SOL   HOLD  Conf: 65%  |  Awaiting confirmation
XRP   SELL  Conf: 72%  |  Target reached, taking profit
```

---

## Command Examples

### Run with all features
```bash
python run_unified_orca.py --autonomous --open-dashboard
```

### Run in dry-run mode (no real trades)
```bash
python run_unified_orca.py --autonomous --dry-run --open-dashboard
```

### Run just the dashboard server (without Orca)
```bash
python unified_dashboard_server.py
# Open: http://localhost:13334
```

### Run just Orca (with separate dashboard)
```bash
# Terminal 1:
python unified_dashboard_server.py

# Terminal 2:
python orca_complete_kill_cycle.py --autonomous
```

---

## API Examples

### Check Orca Status
```bash
curl http://localhost:13334/api/orca-status
```

Response:
```json
{
  "status": "running",
  "ready_for_execution": true,
  "blockers": [],
  "active_positions": 3,
  "total_pnl": 1247.50,
  "timestamp": "2026-03-23T12:45:30.123456"
}
```

### Get Unified State
```bash
curl http://localhost:13334/api/unified-state
```

Response:
```json
{
  "timestamp": "2026-03-23T12:45:30.123456",
  "coordination": {
    "total_systems": 197,
    "orca_ready": true,
    "state_counts": {...}
  },
  "decisions": {
    "BTC": {"type": "buy", "confidence": 0.85, ...},
    "ETH": {"type": "buy", "confidence": 0.78, ...}
  },
  "feeds": {
    "market_data": {"is_healthy": true, "event_count": 342},
    "intelligence": {"is_healthy": true, "event_count": 156},
    ...
  },
  "uptime": 245.67
}
```

### Send Command
```bash
curl -X POST http://localhost:13334/api/orca-command \
  -H "Content-Type: application/json" \
  -d '{"command": "stop"}'
```

---

## Troubleshooting

### Dashboard shows "API connection failed"

**Check:**
```bash
curl http://localhost:13334/api/health
```

**Solution:** Make sure server is running:
```bash
python unified_dashboard_server.py
```

### "Orca not ready" with blockers

**Cause:** Exchange clients haven't initialized
**Fix:** Wait 10-15 seconds, refresh dashboard. They auto-initialize.

### Metrics not updating in real-time

**Fix:** Refresh browser (Ctrl+R or Cmd+R)

### Port 13334 already in use

**Find and kill process:**
```bash
lsof -i :13334          # Find process
kill -9 <PID>           # Kill it
```

---

## Performance Characteristics

| Metric | Value |
|--------|-------|
| Dashboard Update Frequency | 1 Hz (every 1 second) |
| API Response Time | <100ms |
| ThoughtBus Throughput | ~100+ messages/second |
| Orca Order Execution Latency | <500ms |
| Memory Usage (all components) | ~200-300 MB |
| CPU Usage (idle) | ~5-10% |
| CPU Usage (trading) | ~20-40% |

---

## Files You'll Use

| File | Purpose |
|------|---------|
| `run_unified_orca.py` | Main launcher - **START HERE** |
| `unified_dashboard_server.py` | Dashboard + API server |
| `dashboard.html` | Browser dashboard interface |
| `orca_complete_kill_cycle.py` | Orca trading engine |
| `aureon_system_coordinator.py` | System state management |
| `aureon_unified_decision_engine.py` | Trading decision logic |
| `aureon_orca_monitor.py` | Orca execution tracking |
| `UNIFIED_DASHBOARD_QUICKSTART.md` | User guide |

---

## Summary

**To see live metrics on the unified dashboard while Orca trades:**

```bash
python run_unified_orca.py --autonomous --open-dashboard
```

**Then open:** http://localhost:13334

**You'll see:**
- ✅ Real-time Orca status
- ✅ System coordination (197 systems)
- ✅ 5 consolidated feed streams
- ✅ Trading decisions with confidence
- ✅ Control buttons (start/stop/pause)
- ✅ Live metrics updating every 1 second

**ThoughtBus flow:** Orca → Coordinator → Decision Engine → API → Browser Dashboard

🎯 **Ready to trade with full visibility!**
