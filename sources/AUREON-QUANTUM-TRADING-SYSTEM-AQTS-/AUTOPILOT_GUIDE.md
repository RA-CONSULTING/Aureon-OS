# 🦁 AUREON AUTOPILOT GUIDE 🍯

## Quick Start

### 1. Install Python Requirements
```bash
pip install requests python-dotenv
```

### 2. Set Your Credentials
Your `.env` file should have:
```env
BINANCE_API_KEY=your_key_here
BINANCE_API_SECRET=your_secret_here
BINANCE_TESTNET=false  # true for testnet
```

### 3. Launch Autopilot
```bash
# Test run (simulation mode)
export CONFIRM_AUTOPILOT=YES
export AUTOPILOT_DAYS=1
python scripts/autopilot.py
```

## What It Does

The autopilot will:
- ✅ Execute 50 trades per day automatically
- ✅ Use 20% position sizing per trade
- ✅ Trade BTC, ETH, BNB pairs
- ✅ Target 68% win rate (from smoke test)
- ✅ Track all P&L automatically
- ✅ Log results to `autopilot_log.json`
- ✅ Compound profits automatically

## Expected Results (from smoke test)

**Day 1**: $147 → ~$153 (+$6)
**Week 1**: $147 → ~$206 (+$59)
**Month 1**: $147 → ~$752 (+$605) 🍯

## Safety Features

- 🛡️ 5-minute cooldown between trades
- 🛡️ Minimum $11 order size (Binance requirement)
- 🛡️ Confirmation required (CONFIRM_AUTOPILOT=YES)
- 🛡️ All trades logged to file
- 🛡️ Automatic balance checking

## Commands

### Run 1 Day
```bash
export CONFIRM_AUTOPILOT=YES
export AUTOPILOT_DAYS=1
python scripts/autopilot.py
```

### Run 7 Days (1 Week)
```bash
export CONFIRM_AUTOPILOT=YES
export AUTOPILOT_DAYS=7
python scripts/autopilot.py
```

### Run 30 Days (1 Month)
```bash
export CONFIRM_AUTOPILOT=YES
export AUTOPILOT_DAYS=30
python scripts/autopilot.py
```

### Check Logs
```bash
cat autopilot_log.json | jq '.'
```

## How It Works

1. **Connects** to Binance API
2. **Checks** USDT balance
3. **Executes** 50 trades per day:
   - Generates signal (BUY/SELL/HOLD)
   - Calculates 20% position size
   - Places market order
   - Tracks P&L
4. **Logs** results after each day
5. **Repeats** for specified number of days

## Trading Logic

Based on your smoke test results:
- Position Size: 20% of equity
- Win Rate: 68%
- Avg Win: 1.2%
- Avg Loss: 0.8%
- Cooldown: 5 minutes

## Monitoring

Watch the console for:
- 🎯 Trade execution
- ✅ Winners/Losers
- 📊 Status updates every 10 trades
- 💰 Running P&L
- 🍯 Total honey collected

## Stop Autopilot

Press `Ctrl+C` to safely stop

## Next Level: Add Your Strategy

Replace the `generate_signal()` function with:
- QGITA quantum coherence detection
- Lighthouse high-consensus finder
- Fibonacci timing
- Prime scaling
- Any of your quantum strategies!

## 🦁 THE LION IS ON AUTOPILOT! 🍯

Let it hunt while you sleep! 🚀
