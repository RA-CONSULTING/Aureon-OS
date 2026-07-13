# 🌊 Aureon Unified Live Dashboard

**ONE interface for everything.** Clean, focused, streaming real metrics.

## Quick Start

```bash
# Start the dashboard
python aureon_unified_live_dashboard.py --port 8080

# Open in browser
http://localhost:8080
```

## What It Does

Consolidates **15+ fragmented dashboards** into ONE clean interface with:

- ✅ **Real-time WebSocket streaming** (2s portfolio updates, 5s system health)
- ✅ **Multi-exchange aggregation** (Kraken + Alpaca + Binance + Capital.com)
- ✅ **Cost basis integration** (REAL entry prices, not estimates)
- ✅ **ThoughtBus bridge** (live events from all systems)
- ✅ **Clean 3-tab interface** (Trading, Intelligence, Systems)
- ✅ **No framework bloat** (vanilla JS + CSS)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│          AUREON UNIFIED LIVE DASHBOARD (Port 8080)          │
├─────────────────────────────────────────────────────────────┤
│  Backend: Python 3.11+ / aiohttp                            │
│  Frontend: Vanilla JS + CSS (no React/Vue/Angular)         │
│  Real-time: WebSocket (/live)                               │
│  API: REST endpoints (/api/*)                               │
│  Bridge: ThoughtBus → WebSocket event stream                │
└─────────────────────────────────────────────────────────────┘
```

## The 3 Tabs

### 📊 TAB 1: TRADING (Default View)

**Portfolio Totals** (live updates every 2 seconds):
- Total Portfolio Value
- Cash Available
- P&L Today
- P&L Total

**Active Positions Table**:
- Exchange (Kraken, Alpaca, Binance, Capital)
- Symbol (BTC/USD, AAPL, etc.)
- Quantity
- Current Price
- Market Value
- **Entry Price** (from cost basis tracker - REAL, not estimated)
- **P&L** (profit/loss in $)
- **P&L %** (profit/loss percentage)

Color-coded P&L: 🟢 Green = profit, 🔴 Red = loss

### 🧠 TAB 2: INTELLIGENCE

**Bot Detection**:
- Active bots count
- Bot percentage of trades
- Firm intelligence (37 firms tracked)
- Whale signals

**Market Analysis**:
- Top movers (rising/falling)
- Momentum scores
- Manipulation alerts

*(Currently placeholder - full integration coming soon)*

### ⚙️ TAB 3: SYSTEMS

**Exchange Health**:
- Kraken: 🟢 Online / 🔴 Offline
- Alpaca: 🟢 Online / 🔴 Offline
- Binance: 🟢 Online / 🔴 Offline
- Capital.com: 🟢 Online / 🔴 Offline

**System Status**:
- ThoughtBus activity
- Queen Hive Mind
- Avalanche Harvester (treasury balance)
- Validation pipeline

## WebSocket Events

The dashboard subscribes to **8 critical ThoughtBus topics** and streams them in real-time:

| Topic | Event Type | Description |
|-------|------------|-------------|
| `market.*` | `market_update` | Market data updates (prices, spreads, volatility) |
| `execution.*` | `trade_executed` | Trade executions across all exchanges |
| `system.*` | `system_health` | System health status changes |
| `whale.sonar.*` | `whale_signal` | Whale/subsystem monitoring signals |
| `harvest.*` | `harvest_event` | Avalanche harvester profit scraping |
| `validation.*` | `validation_update` | Queen validation pipeline (3→4th pass) |
| `bot.*` | `bot_detected` | Bot detection events |
| `position.*` | `position_update` | Position changes (entry/exit) |

## REST API Endpoints

For on-demand data access:

```bash
# Portfolio data
curl http://localhost:8080/api/portfolio

# System health
curl http://localhost:8080/api/systems

# Intelligence data
curl http://localhost:8080/api/intelligence
```

## Metrics Streaming Schedule

| Metric | Update Frequency | Description |
|--------|------------------|-------------|
| Portfolio totals | Every 2 seconds | Total value, cash, P&L (today/total) |
| Active positions | Every 2 seconds | All positions with live P&L |
| System health | Every 5 seconds | Exchange status, system modules |
| ThoughtBus events | Real-time | Instant broadcasts (trades, harvests, bots) |

## Integration Points

The dashboard **lazy-loads** systems on demand (fast startup):

```python
# Lazy system loading
@property
def queen(self):
    """Load Queen Hive Mind when first accessed"""
    if self._queen is None:
        from aureon_queen_hive_mind import QueenHiveMind
        self._queen = QueenHiveMind()
    return self._queen

# Same pattern for:
# - Cost Basis Tracker
# - Avalanche Harvester
# - Exchange clients (Kraken, Alpaca, Binance, Capital)
```

**Benefits**:
- Server starts in ~2 seconds (no blocking imports)
- Systems loaded only when needed
- Graceful degradation if system unavailable

## Design Philosophy

### Simplify
- 3 tabs instead of 6+
- ONE dashboard instead of 15+
- 10 core components instead of 150+

### Stream
- Real-time WebSocket updates
- ThoughtBus event bridge
- Auto-reconnecting on disconnect

### Integrate
- Queen Hive Mind
- Cost Basis Tracker (real entry prices)
- Avalanche Harvester (treasury)
- All 4 exchanges (Kraken, Alpaca, Binance, Capital)

### Consistency
- Uses same logic as Batten Matrix/Queen systems
- Unified data model across exchanges
- Coherent design language

## What This Replaces

**Old fragmented dashboards** (now deprecated):
- ❌ `aureon_command_center.py` (old version)
- ❌ `aureon_command_center_enhanced.py` (old version)
- ❌ `aureon_command_center_lite.py` (too simple)
- ❌ `aureon_queen_realtime_command_center.py` (terminal-only)
- ❌ `queen_profit_dashboard.py` (terminal-only)

**Still useful as specialized tools**:
- ✅ `aureon_command_center_ui.py` (5663 lines - advanced features)
- ✅ `queen_web_dashboard.py` (bot intelligence focus)
- ✅ `orca_command_center.py` (hunting-specific UI)

**This unified dashboard** is the **NEW PRIMARY INTERFACE** for:
- Day-to-day trading monitoring
- Portfolio tracking
- System health checks
- Quick metric glances

## Command Line Options

```bash
# Default (port 8080, all interfaces)
python aureon_unified_live_dashboard.py

# Custom port
python aureon_unified_live_dashboard.py --port 9000

# Localhost only (security)
python aureon_unified_live_dashboard.py --host 127.0.0.1 --port 8080

# Help
python aureon_unified_live_dashboard.py --help
```

## Browser Compatibility

Tested and working:
- ✅ Chrome/Edge (Chromium)
- ✅ Firefox
- ✅ Safari
- ✅ Mobile browsers (responsive design)

## Troubleshooting

### Dashboard won't start

```bash
# Check if port is already in use
lsof -i :8080

# Kill existing process
kill <PID>

# Try different port
python aureon_unified_live_dashboard.py --port 9000
```

### WebSocket keeps disconnecting

**Check**: ThoughtBus availability
```python
# Dashboard logs will show:
# "✓ ThoughtBus bridge initialized (8 topics)" = Good
# "ThoughtBus not available: ..." = ThoughtBus not running
```

**Solution**: ThoughtBus is optional - dashboard still works without it (REST API only)

### No positions showing

**Check**: Exchange client credentials
```bash
# Kraken: KRAKEN_API_KEY, KRAKEN_API_SECRET
# Alpaca: ALPACA_API_KEY, ALPACA_API_SECRET
# Binance: BINANCE_API_KEY, BINANCE_API_SECRET
# Capital: CAPITAL_API_KEY, CAPITAL_IDENTIFIER, CAPITAL_PASSWORD
```

**Solution**: Set environment variables in `.env` file

### P&L shows "--" instead of values

**Reason**: Cost basis tracker doesn't have entry price for that position

**Solution**: 
1. Position was opened before cost basis tracking started (no historical data)
2. Buy more of that asset (cost basis will track new buys)
3. Entry price will show "0.00" until real buy is tracked

## Performance Tips

1. **Lazy Loading**: Systems load on first access (fast startup)
2. **Efficient Broadcasting**: WebSocket sends data only to connected clients
3. **Cached Metrics**: Portfolio data cached and reused across clients
4. **Throttled Updates**: 2s portfolio, 5s systems (balanced performance)

## Security Notes

**Development Mode**:
- Default: Binds to `0.0.0.0` (all interfaces)
- Accessible from network

**Production Mode**:
```bash
# Localhost only
python aureon_unified_live_dashboard.py --host 127.0.0.1

# Or use reverse proxy (nginx, caddy)
# with HTTPS + authentication
```

## Future Enhancements

**Phase 2** (Intelligence Tab):
- [ ] Bot detection integration
- [ ] Whale sonar visualization
- [ ] Firm intelligence cards
- [ ] Market manipulation alerts

**Phase 3** (Advanced Features):
- [ ] Real-time charts (ApexCharts)
- [ ] Audio alerts (trade execution, harvests)
- [ ] Queen voice commentary (TTS)
- [ ] Orca hunting mode (optional tab)

**Phase 4** (Polish):
- [ ] User preferences (theme, intervals)
- [ ] Alert configurations
- [ ] Export/download data
- [ ] Mobile app (React Native)

## Integration Flow

```
┌──────────────────────────────────────────────────────────────┐
│                    AUREON TRADING SYSTEM                      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐      ┌──────────────┐                     │
│  │ Queen Hive   │◄────►│ ThoughtBus   │                     │
│  │ Mind         │      │ (Events)     │                     │
│  └──────────────┘      └──────┬───────┘                     │
│         │                     │                              │
│         │              ┌──────▼───────┐                      │
│         │              │ Unified      │                      │
│         │              │ Dashboard    │                      │
│         │              │ (WebSocket)  │                      │
│         │              └──────┬───────┘                      │
│         │                     │                              │
│  ┌──────▼──────┐       ┌─────▼──────┐                       │
│  │ Cost Basis  │       │ Browser    │                       │
│  │ Tracker     │       │ Clients    │                       │
│  └──────┬──────┘       └────────────┘                       │
│         │                                                    │
│  ┌──────▼──────────────────────────────────┐                │
│  │  Avalanche Harvester                    │                │
│  └──────┬──────────────────────────────────┘                │
│         │                                                    │
│  ┌──────▼──────┬──────────┬──────────┬──────────┐          │
│  │  Kraken     │  Alpaca  │ Binance  │ Capital  │          │
│  │  Client     │  Client  │ Client   │ Client   │          │
│  └─────────────┴──────────┴──────────┴──────────┘          │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## Summary

**Before**: 15+ fragmented dashboards, 150+ React components, no consistency

**After**: ONE unified interface, 3 clean tabs, real-time streaming, consistent design

**Result**: Simplified monitoring, faster development, better user experience

---

**Created by**: Gary Leckey & GitHub Copilot  
**Date**: January 24, 2026  
**Commit**: 6cc8812 🌊
