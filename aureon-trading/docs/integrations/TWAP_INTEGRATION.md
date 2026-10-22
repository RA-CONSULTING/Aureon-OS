# 📊 TWAP Integration - Intelligent Order Execution

## Overview

AUREON now features **Binance Algo TWAP (Time-Weighted Average Price)** integration for intelligent large order execution. Orders above the configured threshold are automatically executed using TWAP to minimize market impact and improve fill quality.

---

## 🎯 How It Works

### Automatic TWAP Routing

1. **Pride Scanner** identifies high-opportunity targets
2. **QGITA** generates trading signals with confidence tiers
3. **Order Size Check**:
   - Order value ≥ $500 → **TWAP Execution**
   - Order value < $500 → **Standard OMS Queue**
4. **TWAP Execution**:
   - Breaks order into smaller sub-orders
   - Executes over configured time period (5min - 24hr)
   - Reduces slippage and market impact

---

## 📋 Database Schema

### `twap_orders` Table

Tracks main TWAP order lifecycle:

```sql
- id (UUID): Unique order ID
- algo_id (BIGINT): Binance algo order ID
- client_algo_id (TEXT): Our unique tracking ID
- hunt_session_id (UUID): Links to hunt session
- oms_order_id (UUID): Links to OMS queue
- symbol (TEXT): Trading pair (e.g., BTCUSDT)
- side (TEXT): BUY or SELL
- total_quantity (NUMERIC): Total order size
- duration_seconds (INT): Execution duration (300-86400s)
- limit_price (NUMERIC): Optional price limit
- executed_quantity (NUMERIC): Amount filled
- executed_amount (NUMERIC): USD value executed
- avg_price (NUMERIC): Average execution price
- algo_status (TEXT): WORKING | FINISHED | CANCELLED | ERROR
- urgency (TEXT): LOW | MEDIUM | HIGH
```

### `twap_sub_orders` Table

Tracks individual sub-order executions:

```sql
- twap_order_id (UUID): Parent TWAP order
- sub_id (INT): Sub-order index
- order_id (BIGINT): Binance order ID
- executed_quantity (NUMERIC): Sub-order fill
- avg_price (NUMERIC): Sub-order price
- fee_amount (NUMERIC): Trading fee
- order_status (TEXT): Fill status
```

---

## 🔧 Configuration

### Hunt Session TWAP Settings

```typescript
// hunt_sessions table
twap_threshold_usd: 500    // Orders ≥ $500 use TWAP
twap_duration_seconds: 600 // 10 minutes default
```

### Customize Per Hunt

```typescript
const huntConfig = {
  minVolatility: 2.0,
  minVolume: 100000,
  maxTargets: 5,
  scanInterval: 300,
  twapThreshold: 500,      // USD threshold
  twapDuration: 600,       // 10 minutes
};
```

---

## 🚀 Edge Functions

### `binance-algo-twap`

Handles Binance Algo Trading API interaction:

**Actions:**

1. **`place`** - Create new TWAP order
   ```typescript
   {
     action: 'place',
     symbol: 'BTCUSDT',
     side: 'BUY',
     quantity: 0.05,
     duration: 600,
     limitPrice: 43000, // optional
     huntSessionId: 'uuid',
   }
   ```

2. **`sync`** - Fetch execution status
   ```typescript
   {
     action: 'sync',
     twapOrderId: 'uuid',
   }
   ```

3. **`cancel`** - Cancel active TWAP order
   ```typescript
   {
     action: 'cancel',
     twapOrderId: 'uuid',
   }
   ```

---

## 📊 Monitoring

### TWAP Monitor Component

Real-time dashboard showing:

- **Active TWAP orders** with live progress bars
- **Fill percentage** (quantity executed / total)
- **Time progress** (elapsed / total duration)
- **Average execution price**
- **Remaining time** countdown
- **Recent completed orders**

Access via: Markets page → Hunt tab → TWAP Monitor panel

---

## 💡 Benefits

### Why TWAP?

1. **Reduced Slippage**
   - Breaks large orders into smaller pieces
   - Avoids moving the market with big orders
   - Better average fill price

2. **Smart Execution**
   - Time-weighted distribution
   - Adapts to market conditions
   - Matches liquidity patterns

3. **Market Impact Minimization**
   - $1000 order in 1 shot → High impact
   - $1000 order over 10min → Low impact
   - Preserves opportunity profitability

4. **Professional Grade**
   - Same tools used by institutional traders
   - Binance Algo Trading infrastructure
   - Sub-order tracking and analytics

---

## 🔐 Security

### API Requirements

```bash
# Required Binance API permissions:
- Spot Trading: ENABLED
- Algo Trading: ENABLED
- Withdrawals: DISABLED (security)

# Required secrets:
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret
```

### RLS Policies

- Users can only view their own TWAP orders
- Orders linked via `hunt_session_id → user_id`
- Service role manages all TWAP operations
- Sub-orders inherit parent order permissions

---

## 📈 Usage Example

### Automated Hunt with TWAP

```typescript
// 1. Start hunt session
await startHunt({
  minVolatility: 3.0,
  minVolume: 200000,
  maxTargets: 3,
  scanInterval: 300,
  twapThreshold: 500,    // Use TWAP for orders ≥ $500
  twapDuration: 900,     // Execute over 15 minutes
});

// 2. System automatically:
// - Scans markets
// - Generates QGITA signals
// - Routes large orders to TWAP
// - Routes small orders to OMS
// - Tracks all executions

// 3. Monitor via UI:
// - Hunt Control: Shows scan stats
// - TWAP Monitor: Shows active TWAPs
// - OMS Monitor: Shows queued orders
```

---

## 🎚️ Tuning Guidelines

### TWAP Duration

**Short Duration (5-10 min):**
- Fast markets
- High urgency
- Smaller orders ($500-$2000)

**Medium Duration (10-30 min):**
- Normal conditions
- Medium orders ($2000-$10000)
- Balanced execution

**Long Duration (30min-24hr):**
- Slow markets
- Very large orders ($10000+)
- Maximum slippage reduction

### Threshold Optimization

**Conservative (≥ $1000):**
- Only use TWAP for truly large orders
- Most orders via OMS
- Lower API usage

**Aggressive (≥ $200):**
- More orders via TWAP
- Better average prices
- Higher API usage

**Default ($500):**
- Balanced approach
- Good for most use cases

---

## 🔄 Integration Flow

```
PRIDE SCANNER
     ↓
Identifies: BTCUSDT, $800 value, 15% volatility
     ↓
QGITA SIGNAL GENERATOR
     ↓
Generates: BUY signal, Tier 1, 85% confidence
     ↓
ORDER ROUTER (automated-hunt-loop)
     ↓
Checks: $800 ≥ $500 threshold?
     ↓
YES → TWAP Execution
     ↓
binance-algo-twap edge function
     ↓
Binance API: POST /sapi/v1/algo/spot/newOrderTwap
     ↓
- Breaks into 10 sub-orders
- Executes over 10 minutes
- Records to twap_orders table
     ↓
TWAP Monitor UI
     ↓
Real-time progress updates every 5 seconds
```

---

## 🧪 Testing

### Testnet TWAP

```bash
# Enable testnet mode
export BINANCE_TESTNET=true

# Start hunt with TWAP
npm run lion:hunt

# Monitor logs for TWAP execution
# Look for: "📊 BTCUSDT using TWAP: $800.00"
```

### Verify TWAP Order

```sql
-- Check active TWAP orders
SELECT 
  symbol,
  side,
  total_quantity,
  executed_quantity,
  algo_status,
  duration_seconds
FROM twap_orders
WHERE algo_status = 'WORKING'
ORDER BY created_at DESC;

-- Check sub-orders
SELECT 
  sub_id,
  executed_quantity,
  avg_price,
  order_status
FROM twap_sub_orders
WHERE twap_order_id = 'your_order_id'
ORDER BY sub_id;
```

---

## 📚 API Reference

See `docs/BINANCE_ALGO_API_REFERENCE.txt` for complete Binance Algo Trading API documentation.

### Key Endpoints Used

1. **POST** `/sapi/v1/algo/spot/newOrderTwap`
   - Weight: 3000 (UID)
   - Creates new TWAP order

2. **GET** `/sapi/v1/algo/spot/subOrders`
   - Weight: 1 (IP)
   - Fetches sub-order execution details

3. **DELETE** `/sapi/v1/algo/spot/order`
   - Weight: 1 (IP)
   - Cancels active TWAP order

---

## 🎯 Next Steps

1. **Test on Testnet**: Verify TWAP execution with small amounts
2. **Monitor Performance**: Track slippage vs standard orders
3. **Tune Parameters**: Adjust threshold and duration based on results
4. **Scale Up**: Increase thresholds as confidence grows

---

## ⚠️ Important Notes

- **Max 20 concurrent TWAP orders** (Binance limit)
- **Min duration: 5 minutes** (300 seconds)
- **Max duration: 24 hours** (86400 seconds)
- **Max notional**: Varies by symbol (200k-10mm)
- **TWAP orders can't be modified**, only cancelled

---

## 📞 Support

For issues or questions:
- Check edge function logs: `supabase functions logs binance-algo-twap`
- Review TWAP orders table: `SELECT * FROM twap_orders ORDER BY created_at DESC`
- Binance API errors: Check `error_code` and `error_message` columns

---

**🦁 THE LION HUNTS WITH INTELLIGENCE 🌈💎**

*Last Updated: November 22, 2025*
*Version: 1.0.0*
*Status: OPERATIONAL ✅*
