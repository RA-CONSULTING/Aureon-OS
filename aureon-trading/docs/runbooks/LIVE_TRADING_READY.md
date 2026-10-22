# AUREON LIVE TRADING SETUP - COMPLETE

**Date:** November 28, 2025  
**System:** Aureon Trading | Master Equation Λ(t) = S(t) + O(t) + E(t)  
**Status:** Ready for deployment with NEW Binance API keys

---

## 🎯 What You Now Have

### 1. Python Binance Integration Layer
- **`binance_client.py`** — Secure, signed REST client with testnet/dry-run controls
  - Account info, balances, price feeds
  - Deposit address retrieval (mainnet only)
  - Market & limit order placement with position sizing
  
- **`binance_trade_sample.py`** — Minimal example to fetch prices & place test trades

- **`binance_get_address.py`** — Retrieve deposit address for funding

### 2. Aureon Live Trading Engine
- **`aureon_live.py`** — Master Equation integration with 9 Auris nodes
  - 3-stage progressive validation (testnet dry-run → testnet real → mainnet live)
  - Coherence testing (Λ(t), Γ thresholds)
  - Comprehensive audit logging to `trade_audit.log`
  - Risk controls: fraction-based sizing, max notional caps

### 3. Security & Documentation
- **`.env.example`** — Template (safe, gitignored)
- **`SECURITY_TRADING.md`** — API key rotation, incident response, best practices
- **`LIVE_TRADING_RUNBOOK.md`** — Step-by-step launch checklist (Stages 0→1→2)
- **`check_live_environment.py`** — Pre-flight validation tool

### 4. Risk Controls (Built-In)
| Control | Default | Purpose |
|---------|---------|---------|
| Testnet by default | true | No mainnet until explicit toggle |
| Dry-run by default | true | No orders until explicitly disabled |
| Risk fraction | 2% | Only risk 2% of free balance per trade |
| Max order USDT | 25 | Cap all orders to 25 USDT max |
| Min notional | 5 USDT | Skip trades below this |
| API key restrictions | Spot only, no withdraw | Enforce on Binance side |

---

## ⚡ 3-Stage Launch Sequence

### Stage 0: Validate Testnet + Dry-Run (No Real Orders)
```bash
export BINANCE_USE_TESTNET=true BINANCE_DRY_RUN=true
python3 aureon_live.py --stage 0 --symbol BTCUSDT --trades 1
# Expected: Coherence test runs, dry-run logged, NO actual order placed
```
**Duration:** 5–10 min | **Goal:** Confirm strategy logic & audit logging work

### Stage 1: Validate Testnet + Real Orders
```bash
export BINANCE_USE_TESTNET=true BINANCE_DRY_RUN=false
python3 aureon_live.py --stage 1 --symbol BTCUSDT --trades 3
# Expected: Real testnet orders placed & executed
```
**Duration:** 30 min–1 hour | **Goal:** Verify order lifecycle on non-real money

### Stage 2: Live Mainnet + Real Capital
```bash
export BINANCE_USE_TESTNET=false CONFIRM_LIVE=yes
python3 aureon_live.py --stage 2 --symbol BTCUSDT --trades 1
# Expected: Real mainnet orders with real capital
```
**Duration:** Ongoing | **Goal:** Generate live P&L with Master Equation

---

## 🔐 Critical Prerequisites for Stage 2

Before running Stage 2, you MUST:

1. ✅ **Generate NEW Binance API keys** (not the exposed ones from earlier)
   - Go to Binance.com → Account → API Management → Create New Key
   
2. ✅ **Restrict API key permissions:**
   - Enable "Spot Trading" only
   - Disable "Futures" and "Margin"
   - **Disable "Allow withdrawal"**
   
3. ✅ **IP whitelist the key:**
   - Add your current IP or VPN IP to the whitelist
   - Do NOT leave "Unrestricted" if possible

4. ✅ **Copy keys to `.env`:**
   ```bash
   cp .env.example .env
   # Edit .env and paste:
   #   BINANCE_API_KEY=YOUR_NEW_KEY
   #   BINANCE_API_SECRET=YOUR_NEW_SECRET
   ```

5. ✅ **Verify with Stage 0 & 1 first** (at least 1 hour on testnet)

6. ✅ **Fund your Binance account:**
   ```bash
   python3 binance_get_address.py BTC  # or USDT, ETH, etc.
   ```
   Transfer funds from your bank to the displayed address.

---

## 📊 Key Files & Their Purpose

| File | Purpose | Audience |
|------|---------|----------|
| `binance_client.py` | Core Binance API wrapper | Developers |
| `aureon_live.py` | Master Equation + trading loop | Traders |
| `LIVE_TRADING_RUNBOOK.md` | Step-by-step launch guide | All |
| `SECURITY_TRADING.md` | Risk & key management | Risk Officers |
| `trade_audit.log` | Complete trade ledger (auto-generated) | Compliance |

---

## 🚀 To Begin

### Immediate (Next 15 minutes)
1. Read `LIVE_TRADING_RUNBOOK.md` — understand the 3 stages
2. Generate NEW Binance API keys (restrict permissions, IP whitelist)
3. Copy `.env.example` → `.env` and fill with new keys
4. Run `python3 check_live_environment.py` to verify setup

### Short-term (Next 1–2 hours)
5. Run Stage 0: `python3 aureon_live.py --stage 0 --symbol BTCUSDT --trades 1`
6. Review `trade_audit.log` to confirm logging works
7. Run Stage 1: `python3 aureon_live.py --stage 1 --symbol BTCUSDT --trades 3`
8. Monitor Binance testnet account for order execution

### Before Live (Next 24 hours)
9. Validate strategy performance on testnet
10. Review all logs for anomalies
11. Fund mainnet Binance account
12. Run Stage 2: `python3 aureon_live.py --stage 2 --symbol BTCUSDT --trades 1`

---

## ⚠️ Safety Reminders

- **NEVER paste real API keys in chat, logs, or issues**
- **NEVER commit `.env` to git** (already in `.gitignore`)
- **Keys are rotating credentials** — rotate quarterly or if exposed
- **Audit logging is mandatory** — review `trade_audit.log` daily
- **Test on testnet first** — at minimum 1 hour before going live
- **Risk-size conservatively** — start with 2% per trade (adjustable)
- **Disable withdrawal on API key** — no emergency access needed

---

## 📞 Troubleshooting

**Q: "Missing BINANCE_API_KEY"**  
A: `.env` file missing or not sourced. Run: `export $(cat .env | xargs)`

**Q: "Coherence test inconclusive"**  
A: Normal on low-volume symbols. System proceeds anyway in Stage 0. Higher threshold (Γ > 0.95) enforced for real trades.

**Q: "Order executed but didn't appear in my balance"**  
A: Check `trade_audit.log` for order ID, then verify on Binance UI. Testnet may have lag.

**Q: "How do I stop trading?"**  
A: Set `BINANCE_DRY_RUN=true` and restart. No new real orders will be placed.

---

## 📈 After Launch

Once Stage 2 is running successfully:
- **Monitor hourly:** Watch `tail -f trade_audit.log` for anomalies
- **Daily P&L:** Log profits/losses to tax tracker
- **Weekly review:** Audit logs for coherence threshold adjustments
- **Monthly rotation:** Refresh API keys if not already done

---

**System Ready. Keys Never Committed. Audit Trail Complete.**  
**You're equipped to trade. Use your new keys wisely. Good luck! 🦆**

