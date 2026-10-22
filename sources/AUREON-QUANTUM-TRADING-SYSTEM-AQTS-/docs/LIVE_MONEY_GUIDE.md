# 🔥 AUREON LIVE: Real Money Deployment Guide

## ⚠️ CRITICAL - READ BEFORE PROCEEDING

This guide activates **REAL MONEY TRADING** on your Binance live account. All trades will execute with actual capital and incur real losses/gains.

---

## 📋 Prerequisites

1. **Live Binance Account** - Not testnet
   - URL: [https://www.binance.com](https://www.binance.com) (not testnet.binance.com)
   - Account verified and funded with USDT

2. **API Keys Generated**
   - Go to: [https://www.binance.com/en/user/settings/api-management](https://www.binance.com/en/user/settings/api-management)
   - Create NEW API key (separate from testnet keys)
   - Enable: Reading Account Info, Placing Orders, Canceling/Querying Orders
   - ✅ Disable IP restrictions (for dev environment) OR add your IP
   - ❌ DO NOT enable withdrawals

3. **Backup & Safety**
   - Backup your .env file: `cp .env .env.backup`
   - Backup your API keys securely
   - Test with SMALL balance first

---

## 🚀 Quick Start (3 Steps)

### Step 1: Generate Live API Keys

1. Go to [https://www.binance.com/en/user/settings/api-management](https://www.binance.com/en/user/settings/api-management)
2. Click "Create API" → API Label: "AUREON-LIVE"
3. Choose "System Generated" (safer)
4. Complete security verification
5. **COPY your API Key & Secret** (you won't see secret again!)

### Step 2: Update .env for Live Trading

```bash
# Edit .env file - MAKE THESE CHANGES:

# Old (testnet):
BINANCE_TESTNET=true
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_API_SECRET=your_binance_api_secret_here

# New (live):
BINANCE_TESTNET=false
BINANCE_API_KEY=YOUR_LIVE_API_KEY_HERE
BINANCE_API_SECRET=YOUR_LIVE_API_SECRET_HERE

# Risk Settings (START CONSERVATIVE)
MAX_ORDER_SIZE=100          # USDT per order - START SMALL!
MAX_DAILY_TRADES=50         # Max trades per day
RISK_LIMIT_PERCENT=0.5      # 0.5% risk per trade
```

### Step 3: Launch Live Trading

```bash
# Confirm you understand the risks
export CONFIRM_LIVE_TRADING=yes

# Start with few steps and short interval
export MAX_STEPS=100
export LOG_INTERVAL=20

# Execute live trading
npx tsx scripts/realMoneyLive.ts
```

---

## 🎯 Live Trading Features

### Real Order Execution

- **Limit Orders** - 1% buffer to ensure fill
- **Position Tracking** - Real-time P&L on live positions
- **Risk Management** - Automatic position sizing based on risk %
- **Daily Limits** - Prevent over-trading

### Multi-Hive Queen Network

- **5 Agents per Hive** - Conservative for live money
- **Auto-Spawning** - When equity grows 5x
- **Real-time Monitoring** - Live P&L tracking
- **Graceful Shutdown** - Closes all positions cleanly

### Safety Mechanisms

1. **Position Size Limits** - Scales down if exceeds max order size
2. **Daily Trade Caps** - Stops trading after limit reached
3. **Risk Percentage** - Each trade risks only 0.5% of agent balance
4. **Confirmation Required** - Must export `CONFIRM_LIVE_TRADING=yes`
5. **Minimum Balance Check** - Requires at least £10 to start

---

## 📊 Live Trading Workflow

### 1. Connection Phase

```text
✅ Connect to LIVE Binance
📊 Fetch real account balance
💰 Display available capital
⏱️  Show configured limits
```

### 2. Hive Initialization

```text
✨ Create initial hive with full balance
👥 Distribute capital across agents (default 5)
📍 Ready to trade
```

### 3. Trading Loop

```text
Per step:
  - Each agent selects random symbol
  - Fetches live market price
  - Calculates position size
  - Executes REAL limit order
  - Tracks P&L and positions

Every 20 steps:
  - Print network status
  - Show real-time metrics
  - Check hive spawning conditions
```

### 4. Hive Spawning

```text
When average agent balance > 5x initial:
  - Harvest 10% of hive equity
  - Create new generation hive
  - Continue exponential growth
```

### 5. Graceful Shutdown

```text
On completion:
  - Close all open positions
  - Calculate total P&L
  - Display final metrics
```

---

## 💡 Trading Symbols

Default symbols for live trading:

- **BTCUSDT** - Bitcoin
- **ETHUSDT** - Ethereum
- **BNBUSDT** - Binance Coin
- **ADAUSDT** - Cardano
- **DOGEUSDT** - Dogecoin

Each with 10% position size allocation (spread across 5 symbols).

---

## 🛑 Emergency Stop

If trading behavior is abnormal:

```bash
# Kill all trading processes
pkill -f "realMoneyLive"

# Check what happened
tail -100 <log-file>

# Manually close positions via Binance app or web
# Go to Binance.com → Spot Trading → Your positions
```

---

## ⚠️ Risk Management Checklist

- [ ] Live API key created (not testnet)
- [ ] .env file updated with LIVE credentials
- [ ] MAX_ORDER_SIZE set to conservative value (start with £100)
- [ ] MAX_DAILY_TRADES limited (start with 50)
- [ ] Backup .env file created
- [ ] CONFIRM_LIVE_TRADING=yes exported
- [ ] Started with MAX_STEPS=100 (short test run)
- [ ] Monitoring terminal output in real-time
- [ ] Kill command ready if needed

---

## 📈 Expected Behavior

### Healthy Metrics

✅ Consistent P&L growth from trades
✅ Win rate stabilizing around 50%+
✅ Hives spawning after 5x equity growth
✅ Agents actively trading on live market
✅ Position sizes scaling with balance

### Warning Signs

❌ Rapid balance decline (> 5% per step)
❌ Frequent failed orders (check API limits)
❌ No trades executing for 10+ steps
❌ API errors in logs
❌ Positions not closing properly

---

## 🔐 Security Best Practices

1. **API Key Security**
   - Never commit .env to git
   - Use IP whitelist if possible
   - Consider sub-account for trading
   - Rotate keys monthly

2. **Fund Management**
   - Trade with small capital first
   - Increase gradually after 1 week of success
   - Never use leverage (no margin)
   - Keep majority in cold storage

3. **Monitoring**
   - Check logs every 30 minutes
   - Review P&L daily
   - Verify positions via Binance app
   - Set alerts for large losses

---

## 📞 Support

If issues occur:

1. **Check Binance API Status**
   - [Binance US Status Page](https://www.binance.us/en/support/announcement/list)

1. **Review Logs**

```bash
# Last 100 lines of execution
tail -100 trading_session.log
```

1. **Verify Credentials**

```bash
# Test connection (safe, read-only)
npx tsx scripts/liveTest.ts
```

1. **Rollback to Testnet**

```bash
# Restore backup .env
cp .env.backup .env
export BINANCE_TESTNET=true
```

---

## 🎉 When It Works

After successful live trading:

1. Monitor daily P&L
2. Log all trades and outcomes
3. Analyze performance metrics
4. Adjust risk limits if needed
5. Reinvest profits or withdraw safely

🔥 **Ready to bring in the honey?** 🍯

Let's GO!
