# AUREON LIVE TRADING RUNBOOK
## Safe Launch Checklist & Operations Guide

---

## ⚡ Quick Start (3 Stages)

### Stage 0: Validate Strategy (Testnet + Dry-Run)
**Goal:** Confirm position sizing, order placement logic, and audit logging work.

```bash
# Copy template and fill with NEW testnet keys (DO NOT use the exposed ones)
cp .env.example .env

# Edit .env - set BINANCE_USE_TESTNET=true, BINANCE_DRY_RUN=true
export $(cat .env | grep -v '^#' | xargs)

# Install dependencies
pip install -r requirements.txt

# Run Stage 0
python aureon_live.py --stage 0 --symbol BTCUSDT --trades 1
```

**Expected Output:**
- ✅ Binance API reachable
- ✅ Free USDT balance displayed
- ✅ Coherence test runs (Λ, Γ shown)
- ✅ Dry-run trade logged (no actual order placed)
- ✅ Entry appended to `trade_audit.log`

**Check:** Open `trade_audit.log` and verify dry-run order recorded.

---

### Stage 1: Validate Order Path (Testnet + Real Orders)
**Goal:** Execute real orders on testnet to verify order lifecycle.

```bash
# Switch to real testnet orders
export BINANCE_DRY_RUN=false

# Run Stage 1 (still on testnet)
python aureon_live.py --stage 1 --symbol BTCUSDT --trades 3
```

**Expected Behavior:**
- Real testnet orders placed & executed
- Order IDs returned
- Testnet balance updated
- All details logged to `trade_audit.log`

**Monitor:** Watch the logs for execution; verify orders on Binance testnet web interface if desired.

---

### Stage 2: Live Money (Mainnet + Real Orders)
**Prerequisites:**
1. ✅ Stage 0 & Stage 1 completed and validated
2. ✅ NEW Binance API key generated (NOT the exposed one from chat)
3. ✅ API key restricted: **SPOT trading only**, **no withdrawals**, **IP whitelisted**
4. ✅ Deposit address retrieved via `python binance_get_address.py BTC` (or your base asset)
5. ✅ Funds transferred from bank → Binance wallet

```bash
# Switch to mainnet
export BINANCE_USE_TESTNET=false

# Enable live confirmation
export CONFIRM_LIVE=yes

# Run Stage 2 with conservative trade count
python aureon_live.py --stage 2 --symbol BTCUSDT --trades 1
```

**⚠️ WARNING:** Real capital will be spent. Verify you have:
- [ ] Reviewed logs from Stage 0 & 1
- [ ] Tested the strategy on testnet for ≥1 hour
- [ ] Limited API key permissions (no withdraw, spot only)
- [ ] IP whitelisted the key
- [ ] Risk-sized orders (BINANCE_RISK_MAX_ORDER_USDT set conservatively)

---

## 🛡️ Risk Controls (Already Enforced)

| Control | Value | Rationale |
|---------|-------|-----------|
| `BINANCE_RISK_FRACTION` | 0.02 (2%) | Risk 2% of free quote per trade |
| `BINANCE_RISK_MAX_ORDER_USDT` | 25 | Cap max order size to 25 USDT |
| Min notional | 5 USDT | Skip orders below this threshold |
| Dry-run mode | On by default | No real trades until explicitly disabled |
| Testnet by default | true | Live mainnet requires explicit toggle |

---

## 📊 Monitoring & Audit

### Real-Time Logs
```bash
# Watch live as trades execute
tail -f trade_audit.log

# Filter for errors
grep ERROR trade_audit.log

# Count executed trades
grep -c "✅ Trade executed" trade_audit.log
```

### Daily Reconciliation
```bash
# Compare logged trades vs. Binance account history
python -c "
import json
with open('trade_audit.log') as f:
    trades = [l for l in f if '✅ Trade executed' in l]
print(f'Logged trades today: {len(trades)}')
"
```

### Withdrawal Safety
- API key has NO withdrawal permission
- Withdrawals require secondary verification (email/2FA)
- Manual withdrawal step on Binance web interface required

---

## 🚨 Incident Response

### If Suspicious Activity Detected
1. **IMMEDIATELY** disable the API key in Binance Account → API Management
2. Export all trade history from Binance
3. Review `trade_audit.log` for unauthorized entries
4. Rotate API key (generate new one)
5. Update `.env` with new key
6. Resume from Stage 0 if strategy logic intact

### If Order Gets Stuck
```bash
# Check Binance account for open orders
python -c "from binance_client import BinanceClient; c = BinanceClient(); print(c.account())"

# Cancel stuck orders via Binance UI (web interface)
# Then restart strategy once account is clear
```

### If Balance Depleted Unexpectedly
1. Pause trading immediately (set `BINANCE_DRY_RUN=true`)
2. Review `trade_audit.log` for last 100 trades
3. Verify coherence thresholds were applied
4. Check if risk-sizing formula needs adjustment
5. Restart with smaller position sizes

---

## 📈 Scaling From Stage 2

Once Stage 2 is running successfully for **24+ hours** with positive P&L:

1. **Increase trade volume gradually** (Stage 2 → Stage 2+ with `--trades 10`)
2. **Add more symbols** (BTCUSDT + ETHUSDT + ADAUSDT)
3. **Monitor daily P&L** and adjust risk per trade if needed
4. **Log profits to separate tracker** for tax/accounting

---

## 🔐 Security Best Practices

- **Never commit `.env`** with real keys (already in `.gitignore`)
- **Rotate keys quarterly** or after any exposure
- **Enable 2FA on Binance account** (not just API key)
- **Use different keys for different systems** (one key per bot)
- **Archive `trade_audit.log`** weekly to cold storage (S3, USB drive, etc.)
- **Review logs monthly** for patterns, anomalies, or compliance

---

## 📞 Support & Questions

- **Lost order?** Check `trade_audit.log` for order ID and lookup on Binance
- **Key compromised?** Rotate immediately; Stage 0 recovery = ~15 min
- **Strategy needs tuning?** Pause with `BINANCE_DRY_RUN=true` and test changes in Stage 0

---

## Reference: Master Equation & Coherence

The system uses **Λ(t) = S(t) + O(t) + E(t)** where:
- **Λ(t)** = unified field state (market dynamics)
- **S(t)** = substrate (9 Auris nodes weighted response)
- **O(t)** = observer (self-referential awareness)
- **E(t)** = echo (momentum memory)
- **Γ** = coherence (field alignment, 0-1 scale)

**Entry condition:** Γ > 0.938  
**Exit condition:** Γ < 0.934

Coherence = measure of market alignment; higher = stronger signal, lower = noise.

---

## 🛰️ Nexus Command Server (WebSocket Control)

The dashboard now talks to a lightweight command gateway so you can start/stop live data streams and launch `aureon_nexus.py` cycles without juggling extra terminals.

### Start the gateway

```bash
npm install              # once, ensures express/cors/ws are available
npm run command-server   # starts server/nexus-command-server.ts (default port 8790)
```

Environment switches:

| Variable | Default | Purpose |
|----------|---------|---------|
| `NEXUS_COMMAND_PORT` | `8790` | HTTP + WebSocket listener port |
| `NEXUS_COMMAND_SOCKET_PATH` | `/command-stream` | WebSocket path consumed by the UI |
| `NEXUS_PYTHON_BIN` | `python3` | Interpreter used when `run_nexus` commands execute |
| `NEXUS_SCRIPT` | `./aureon_nexus.py` | Script launched for long-running cycles |

### REST endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/command-center/status` | Snapshot of stream state, clients, and command queue |
| `POST` | `/api/command-center/stream/start` | Body `{ "intervalMs": 150 }` to begin pushing AQTS data ticks |
| `POST` | `/api/command-center/stream/stop` | Halt streaming without killing the server |
| `POST` | `/api/command-center/nexus/run` | Body `{ "cycles": 10, "interval": 5, "symbol": "BTCUSDT" }` to spawn `aureon_nexus.py` |
| `POST` | `/api/command-center/nexus/stop` | Send SIGINT to the active Python worker |

Example: start the stream locally.

```bash
curl -X POST http://localhost:8790/api/command-center/stream/start \
    -H 'Content-Type: application/json' \
    -d '{"intervalMs":150}'
```

### WebSocket commands

- URL: `ws://localhost:8790/command-stream` (override with `VITE_NEXUS_SOCKET_URL` in `.env`)
- Client → server payload: `{ "type": "command", "command": "start_stream", "payload": { "intervalMs": 150 } }`
- Server events: `system_status`, `stream_tick`, `command_update`, `command_log`

If the gateway is offline, the UI automatically falls back to the legacy in-browser simulator so you can continue demos without backend services.

---

**Last Updated:** November 28, 2025  
**System:** Aureon Trading | Master Equation | 9 Auris Nodes  
**Author:** Gary Leckey | R&A Consulting

