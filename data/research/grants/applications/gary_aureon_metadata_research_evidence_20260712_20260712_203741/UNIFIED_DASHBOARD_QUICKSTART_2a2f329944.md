# 🎯 Aureon Unified Dashboard - Quick Start Guide

## Overview

The Unified Dashboard provides real-time monitoring and control of the Orca kill cycle trading system with live metrics streaming through ThoughtBus.

## What You'll See

When running the unified system, you get:

- **🐋 Orca Status Panel** - Live execution state, readiness, and any blockers
- **🔗 System Coordination** - All 197+ systems status, dependencies, health %
- **📡 Feed Status** - 5 consolidated feed streams (market_data, intelligence, risk_metrics, execution_status, system_health)
- **📊 Trading Decisions** - Real-time buy/sell/hold decisions with confidence scores
- **🎮 Control Buttons** - Start/stop/pause Orca execution
- **⚡ Live Metrics** - Real-time updates streaming at 1 Hz

## Quick Start (Recommended)

### Method 1: Full Integration Launcher (Best)

Start everything with a single command:

```bash
python run_unified_orca.py --autonomous --open-dashboard
```

This starts:
1. ✅ System Coordinator (monitors 197 systems)
2. ✅ Decision Engine (generates trading decisions)
3. ✅ Orca Monitor (tracks Orca execution)
4. ✅ Unified Dashboard API (port 13334)
5. ✅ Orca Kill Cycle (autonomous mode)
6. 🌐 Opens dashboard in browser

**Wait for all services to start (~5 seconds), then the dashboard opens automatically.**

### Method 2: Manual Multi-Terminal Setup

If you prefer to run components in separate terminals:

**Terminal 1 - Dashboard Server:**
```bash
python unified_dashboard_server.py
# Output: 🎯 AUREON UNIFIED DASHBOARD SERVER
# Open: http://localhost:13334
```

**Terminal 2 - Orca Kill Cycle:**
```bash
python orca_complete_kill_cycle.py --autonomous
```

**Terminal 3 (Optional) - Monitor Components:**
```bash
python test_unified_dashboard.py
```

Then open your browser to: `http://localhost:13334`

### Method 3: Dry-Run Testing (Safe)

Test with no real trades:

```bash
python run_unified_orca.py --autonomous --dry-run --open-dashboard
```

## What Happens

### System Startup (First 5-10 seconds)

```
[1] System Coordinator loading...
    ✅ Loaded 197 systems from registry
    ✅ Kraken client → READY
    ✅ Binance client → READY
    ✅ Alpaca client → READY

[2] Decision Engine starting...
    ✅ Ready to synthesize market signals

[3] Orca Monitor starting...
    ✅ Listening for Orca execution events

[4] Dashboard API starting...
    ✅ API running on http://localhost:13334

[5] Orca Kill Cycle starting...
    ✅ Market streaming: Kraken + Binance
    ✅ Monitoring 100+ trading pairs
```

### Live Metrics Flow

During execution, you see:

```
Market Data
    ↓
Decision Engine
    ↓
ThoughtBus (decisions.trading)
    ↓
Dashboard API (/api/unified-state)
    ↓
Browser Dashboard (updates every 1 second)
```

## Dashboard Interface

### Status Bar (Top)
Shows 4 real-time metrics:
- **🐋 Orca Status** - Current state (idle/starting/running/stopping/stopped)
- **🔗 System Coordination** - Ready/Not Ready + healthy system count
- **📡 Feeds** - Health status of 5 feed streams
- **⚡ Overall** - Combined readiness (GO/WAIT)

### Three-Panel View (Center)

**Left Panel - Orca Kill Cycle Control**
- Status display
- Ready for execution? (YES/NO with green/red)
- Blockers list (if not ready)
- Control buttons: ▶️ Start | ⏹️ Stop | ⏸️ Pause | 🔄 Refresh

**Center Panel - System Coordination**
- Total systems count
- Healthy systems count
- Health percentage
- State distribution breakdown

**Right Panel - Feed Status**
- All 5 consolidated feeds with:
  - 🟢 Green dot = healthy
  - 🔴 Red dot = unhealthy
  - Event counts per feed

### Bottom Panels

**Left - Recent Decisions**
- Last 5 trading decisions
- Symbol, direction (BUY/SELL/HOLD), confidence %
- Color-coded: Green for BUY, Red for SELL, Yellow for HOLD

**Right - Live Metrics**
- API connection status
- Update frequency (1/sec)
- Last update timestamp

## API Endpoints

All endpoints return JSON and support real-time polling:

### Dashboard View
- `GET /` - Main dashboard HTML
- `GET /dashboard` - Alias
- `GET /unified` - Alias

### Orca Management
- `GET /api/orca-status` - Orca execution state
- `POST /api/orca-command` - Send start/stop/pause commands
  ```bash
  curl -X POST http://localhost:13334/api/orca-command \
    -H "Content-Type: application/json" \
    -d '{"command": "start"}'
  ```

### System Coordination
- `GET /api/system-coordination` - Multi-system state
- `GET /api/system-health` - System health metrics

### Trading Data
- `GET /api/decisions` - All trading decisions
- `GET /api/decisions/BTC` - Decision for specific symbol
- `GET /api/feed-status` - All 5 feed stream status

### Unified State
- `GET /api/unified-state` - Complete system snapshot
- `GET /api/health` - API health check

## Key ThoughtBus Topics

All metrics flow through ThoughtBus for real-time distribution:

```
orca.state_change          # Orca state transitions
orca.position_event        # Position opened/closed/updated
orca.monitor               # Periodic Orca status
coordination.state_change  # System state changes
coordination.monitor       # Periodic coordination state
decisions.trading          # Trading decisions
decisions.monitor          # Periodic decision state
feeds.consolidated.*       # Consolidated feed streams
```

## Troubleshooting

### "API connection failed" in dashboard

**Cause:** Dashboard server not running
**Fix:** Make sure to start the server:
```bash
python unified_dashboard_server.py
```

### "Orca not ready" (blockers shown)

**Cause:** Exchange clients not initialized
**Fix:** The System Coordinator will mark them as READY once exchange APIs connect. This is automatic.

### Metrics not updating in real-time

**Cause:** Polling interval may be too slow
**Fix:** Refresh the browser (F5) - dashboard updates every 1 second

### Port 13334 already in use

**Cause:** Another process on port 13334
**Fix:** Kill the process or use a different port:
```bash
python unified_dashboard_server.py --port 13335
```

## Performance

- **Dashboard Update Frequency:** 1 Hz (every 1 second)
- **API Response Time:** <100ms typical
- **ThoughtBus Throughput:** ~100 messages/second
- **Memory Usage:** ~150-200MB for all components

## Production Deployment

For production deployment:

1. **Use a process manager** (systemd, supervisor, PM2):
```bash
# systemd service file example
[Service]
ExecStart=python /path/to/run_unified_orca.py --autonomous
Restart=on-failure
User=trading
```

2. **Use an HTTP proxy** (nginx, Apache):
```nginx
location / {
    proxy_pass http://localhost:13334;
}
```

3. **Enable HTTPS** with SSL certificates

4. **Monitor system metrics** with external tools:
   - Prometheus scraping `/api/health`
   - Grafana dashboards
   - Log aggregation (ELK stack)

## Advanced Usage

### Monitor specific components

```bash
# Just the API server
python unified_dashboard_server.py

# Just the Orca Monitor
python -c "from aureon_orca_monitor import OrcaMonitor; import asyncio; asyncio.run(OrcaMonitor().monitor_orca())"

# Just the Decision Engine
python -c "from aureon_unified_decision_engine import UnifiedDecisionEngine; import asyncio; asyncio.run(UnifiedDecisionEngine().monitor_decisions())"
```

### Custom integrations

Integrate with your own trading systems:

```python
from aureon_unified_decision_engine import UnifiedDecisionEngine, SignalInput

engine = UnifiedDecisionEngine()

# Add signals from your system
signal = SignalInput(
    source="my_system",
    symbol="BTC",
    direction="bullish",
    strength=0.85
)
engine.add_signal(signal)

# Get decisions
decision = engine.generate_decision("BTC", DecisionType.BUY, DecisionReason.SIGNAL_STRENGTH)
```

## Key Files

- **run_unified_orca.py** - Main launcher (start here!)
- **unified_dashboard_server.py** - Dashboard & API server
- **dashboard.html** - Dashboard interface
- **aureon_system_coordinator.py** - System coordination
- **aureon_unified_decision_engine.py** - Trading decisions
- **aureon_orca_monitor.py** - Orca execution monitoring
- **test_unified_dashboard.py** - Integration tests

## Support

For issues or questions:

1. Check dashboard logs in terminal
2. Verify API health: `http://localhost:13334/api/health`
3. Check ThoughtBus topics for real-time events
4. Run test suite: `python test_unified_dashboard.py`

---

**🎯 Ready to run? Start here:**

```bash
python run_unified_orca.py --autonomous --open-dashboard
```

**Then open:** http://localhost:13334
