# AUREON Live Trading - Binance Integration Guide

## Quick Start

### 1. Set Up Binance API Credentials

Create a `.env` file (or export variables):

```bash
# TESTNET (recommended for initial testing)
export BINANCE_API_KEY="your_binance_testnet_api_key"
export BINANCE_API_SECRET="your_binance_testnet_api_secret"
export BINANCE_TESTNET="true"

# PRODUCTION (live trading - use with caution)
# export BINANCE_TESTNET="false"  # Switch to live
```

### 2. Get API Keys from Binance

#### Testnet (Safe for Development)
1. Go to https://testnet.binance.vision/
2. Login with your regular Binance account
3. Generate API Key and Secret
4. Enable "Spot Trading" permissions
5. Add your IP to whitelist (optional but recommended)

#### Production (Live Trading - Extra Caution)
1. Go to https://www.binance.com/
2. Account → API Management
3. Create a new API key
4. Enable only required permissions:
   - ✅ Spot trading
   - ✅ Enable reading
   - ✅ Margin trading (if needed)
5. **CRITICAL**: Add your IP to whitelist
6. Consider IP whitelisting for additional security
7. Keep Secret Key secure (never commit to git!)

### 3. Run Testnet Demo

```bash
# Install dependencies (if not already done)
npm ci

# Run live trading demo (testnet mode)
BINANCE_API_KEY="your_key" BINANCE_API_SECRET="your_secret" npx tsx scripts/liveTrading.ts
```

Expected output:
```
╔═══════════════════════════════════════════════════════════════╗
║     AUREON LIVE TRADING: Binance Integration Demo            ║
║     Production-Grade Queen-Hive Network + Real Execution    ║
╚═══════════════════════════════════════════════════════════════╝

✅ Binance TESTNET connected. Trader: true
📊 Subscribing to real-time price feeds...
📈 Executing: BUY 0.001 BTCUSDT
✅ Trade 1 executed...
```

### 4. Monitor Positions & Account

The `liveTradingService` provides:
- Real-time price subscriptions (WebSocket)
- Account balance tracking
- Position monitoring (unrealized P&L)
- Order execution & status
- Risk limit enforcement

```typescript
import { liveTradingService } from './core/liveTradingService';

// Initialize
await liveTradingService.initialize();

// Get account balance
const account = await liveTradingService.getAccountInfo();

// Subscribe to live price
liveTradingService.subscribeToPrice('BTCUSDT', (price) => {
  console.log(`BTC price: $${price}`);
});

// Execute trade
const result = await liveTradingService.executeTrade({
  symbol: 'BTCUSDT',
  side: 'BUY',
  quantity: 0.001,
  type: 'MARKET',
});

// Get current positions
const positions = liveTradingService.getPositions();
```

---

## Architecture

### 1. **BinanceClient** (`core/binanceClient.ts`)
- Low-level REST API wrapper
- WebSocket price feed subscriptions
- HMAC-SHA256 signature generation
- Order placement, cancellation, status

### 2. **LiveTradingService** (`core/liveTradingService.ts`)
- High-level trading interface
- Environment-based credential management
- Paper mode fallback (no live execution)
- Position tracking & P&L calculation
- Graceful error handling

### 3. **Environment Config** (`core/environment.ts`)
- Centralized configuration from env variables
- Support for development/testnet/production modes
- Structured logging with levels

### 4. **Live Trading Script** (`scripts/liveTrading.ts`)
- Demo integration showing:
  - Account initialization
  - Real-time price subscriptions
  - Automated trade execution
  - Hive network orchestration

---

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BINANCE_API_KEY` | - | Binance API key |
| `BINANCE_API_SECRET` | - | Binance API secret |
| `BINANCE_TESTNET` | `true` | Use testnet (safer) or live |
| `PAPER_MODE` | `true` | No live execution (safe mode) |
| `NODE_ENV` | `development` | Environment mode |
| `LOG_LEVEL` | `info` | Logging level: debug, info, warn, error |
| `MAX_ORDER_SIZE` | `10000` | Max order notional (£) |
| `MAX_DAILY_TRADES` | `1000` | Max trades per day |
| `RISK_LIMIT_PERCENT` | `2` | Max % of capital per trade |

---

## Safety Features

### Paper Mode (Default)
- No live execution without explicit credentials
- Falls back gracefully if API keys missing
- Simulates trades for testing

### Testnet Trading
- Real API integration without real money
- Identical to production infrastructure
- Perfect for validation before going live

### Risk Limits
- Max order size enforcement
- Daily trade limit
- Position-level risk caps
- Account balance checks before execution

---

## Common Errors & Solutions

### "Cannot find module '../types'"
```bash
# Run type-check to verify setup
npx tsc --noEmit
```

### "Binance API error (401): Invalid API-key"
- ✅ Verify API key is correct and active
- ✅ Check if it's for testnet or production (mismatched)
- ✅ Ensure credentials are exported to shell

### "WebSocket connection failed"
- ✅ Check internet connection
- ✅ Verify Binance WebSocket endpoint is reachable
- ✅ Check firewall/proxy settings

### "Order rejected - insufficient balance"
- ✅ Check account balance with `getAccountInfo()`
- ✅ Verify order quantity is within limits
- ✅ Check if funds are locked in other orders

---

## Next Steps

### 1. Validate Testnet Integration
```bash
BINANCE_API_KEY="..." BINANCE_API_SECRET="..." npx tsx scripts/liveTrading.ts
```

### 2. Integrate with Queen-Hive
- Connect live prices to agent decision-making
- Execute spawning/harvesting with real capital
- Track real P&L + hive performance

### 3. Production Deployment
- Switch to live mode: `BINANCE_TESTNET=false`
- Deploy with secure credential management
- Enable comprehensive logging & alerting
- Run with strict risk limits initially

### 4. Monitor & Scale
- Track hive performance metrics
- Optimize position sizing & spawning thresholds
- Scale to 100+ hives as confidence grows

---

## Security Checklist

- [ ] API keys stored in `.env` (never commit)
- [ ] IP whitelist enabled on Binance account
- [ ] Testnet validated before going live
- [ ] Risk limits properly configured
- [ ] Daily trade limits set
- [ ] Monitoring/alerting enabled
- [ ] Backup communication channel ready (email/SMS)

---

**Ready to bring the fire to Binance? 🔥**

```bash
npm run build && BINANCE_TESTNET=true npx tsx scripts/liveTrading.ts
```
