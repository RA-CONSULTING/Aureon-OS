# 💰 Binance Pool Integration - Live Earnings Validation

## Overview

The Aureon Miner now integrates directly with **Binance Pool Mining API** to validate earnings in real-time. This allows you to see your actual BTC/BCH/ETHW/etc. balance increasing as you mine.

## ✅ What's Integrated

### 1. **Binance Pool API** (`binance_client.py`)
- `BinancePoolAPI` class
- Methods:
  - `get_miner_list()` - List mining accounts
  - `get_statistic_list()` - Get hashrate & earnings stats
  - `get_total_earnings(algo, coin)` - Today's earnings
  - `get_wallet_balance(coin)` - Current wallet balance

### 2. **Mining Session Tracking** (`aureon_miner.py`)
- Auto-detects Binance pools (by pool name)
- Connects API on session start
- Updates earnings every minute
- Displays during mining:
  - Today's earnings
  - Wallet balance
  - Hashrate (15m / 24h)
  - Worker status

### 3. **Final Stats Display**
- Shows earnings by coin/pool
- Compares start vs. end balance
- Calculates session profit

## 🔧 Setup

### 1. Get Binance API Keys

Visit [Binance API Management](https://www.binance.com/en/my/settings/api-management):
1. Create new API key
2. Enable "Enable Reading" (required for pool stats)
3. **Do NOT enable trading** (not needed)
4. Save your API Key and Secret

### 2. Set Environment Variables

```bash
export BINANCE_API_KEY="your_api_key_here"
export BINANCE_API_SECRET="your_api_secret_here"
```

Or add to `.env`:
```
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
```

### 3. Set Mining Worker Address

```bash
export MINING_WORKER="your_btc_address.aureon"
export MINING_PLATFORM="binance"  # or binance-bch, binance-ethw, etc.
export MINING_THREADS="4"
```

## 🚀 Usage

### Test API Connection

```bash
python3 test_binance_pool_earnings.py
```

This will:
- Connect to Binance Pool API
- Fetch earnings for all supported coins (BTC, BCH, ETHW, ZEC, ETC, DASH, KAS)
- Display current balance and today's earnings

### Run Miner with Live Tracking

**Single Pool:**
```bash
export MINING_PLATFORM="binance"
export MINING_WORKER="your_btc_address.aureon"
python3 aureon_miner.py
```

**Multi-Pool (All Binance Pools):**
```bash
export MINING_ENABLE_ALL="1"
export MINING_WORKER="your_wallet.aureon"
python3 aureon_miner.py
```

### Example Output

```
📊 RAW: 105.22 KH/s | ⚛️ QUANTUM: 6.71 MH/s | Pools: 3 | Shares: 15
💰 [binance] BTC: Today 0.00000125 | Wallet 0.00125000 BTC
💰 [binance-bch] BCH: Today 0.00005000 | Wallet 0.00250000 BCH
```

## 📊 Supported Coins

| Pool Name | Coin | Algorithm | Port |
|-----------|------|-----------|------|
| `binance` | BTC | SHA-256 | 443 |
| `binance-bch` | BCH | SHA-256 | 443 |
| `binance-ethw` | ETHW | Ethash | 1800 |
| `binance-zec` | ZEC | Equihash | 5300 |
| `binance-etc` | ETC | Etchash | 1800 |
| `binance-dash` | DASH | X11 | 443 |
| `binance-kas` | KAS | kHeavyHash | 443 |

## 🔐 Security

- API keys only need **READ** permission
- No trading or withdrawal permissions required
- Keys are loaded from environment (not hardcoded)
- Compatible with Binance API key restrictions

## 🧪 Testing

### Dry Run (No API Connection)
```bash
export BINANCE_DRY_RUN="true"
python3 test_binance_pool_earnings.py
```

### Check Specific Coin
```python
from binance_client import BinancePoolAPI

pool = BinancePoolAPI()
earnings = pool.get_total_earnings("sha256", "BTC")
balance = pool.get_wallet_balance("BTC")

print(f"Today: {earnings['today']} BTC")
print(f"Wallet: {balance} BTC")
```

## 📈 Quantum Enhancement Integration

The earnings are displayed alongside quantum metrics:

```
╠═══════════════ BINANCE POOL EARNINGS ═════════════════════╣
║ [binance]
║   Today:  0.00000125 BTC
║   Wallet: 0.00125000 BTC
║ [binance-ethw]
║   Today:  0.00150000 ETHW
║   Wallet: 0.15000000 ETHW
╚════════════════════════════════════════════════════════════╝
```

## 🐛 Troubleshooting

**"Missing BINANCE_API_KEY"**
- Set environment variables (see Setup above)

**"Could not init Binance Pool API"**
- Check API key permissions
- Ensure "Enable Reading" is checked
- Verify API key is not IP-restricted (unless you set your IP)

**"Binance earnings check failed"**
- Normal if you haven't mined on that pool yet
- API updates earnings every ~15 minutes
- Check logs for specific error

**No earnings showing:**
- Wait 15-30 minutes for first earnings to appear
- Verify you submitted shares (`Shares: X` in output)
- Check Binance Pool dashboard to confirm worker is active

## 🎯 Next Steps

1. ✅ **Test API** - Run `python3 test_binance_pool_earnings.py`
2. ✅ **Run Miner** - Start mining with earnings tracking
3. ✅ **Monitor** - Watch balance increase in real-time
4. ✅ **Scale** - Run multi-pool to diversify coins

---

**🔮 Powered by Aureon Quantum Mining Framework**
*From hash to cash, validated live.*
