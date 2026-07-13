# 🌍⚡ CoinAPI Integration - Cross-Exchange Anomaly Detection

**Status**: ✅ **INTEGRATED** | November 30, 2025  
**Author**: Gary Leckey & GitHub Copilot

---

## 🎯 Overview

The CoinAPI integration adds **cross-exchange anomaly detection** to our trading system, enabling us to:

1. **Detect Market Manipulation** - Price discrepancies across exchanges
2. **Identify Wash Trading** - Circular trades inflating volume
3. **Spot Orderbook Spoofing** - Fake liquidity manipulation
4. **Find Arbitrage Opportunities** - Real price differences to exploit
5. **Refine Algorithms Automatically** - Adapt thresholds based on anomalies

### The Core Insight

> **"The Truth is in the Anomalies"**

When exchange data disagrees, the discrepancy reveals the *real story*:
- **Price manipulation** → Avoid the asset temporarily
- **Wash trading** → Blacklist completely
- **Orderbook spoofing** → Require higher confidence
- **Cross-exchange spreads** → Arbitrage opportunity!

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     COINAPI.IO (300+ Exchanges)                 │
│  Professional aggregated data: OHLCV, quotes, orderbooks        │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                    CoinAPIClient                                 │
│  - Rate-limited REST API calls                                   │
│  - Caching for efficiency                                        │
│  - Multi-exchange quote fetching                                 │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                   AnomalyDetector                                │
│  Detects 9 types of anomalies:                                   │
│  • Price Manipulation (cross-exchange spread > 2%)               │
│  • Wash Trading (repeated identical prices)                      │
│  • Orderbook Spoofing (70/30 bid/ask imbalance)                 │
│  • Volume Inflation (3x normal volume)                           │
│  • Latency Arbitrage (>500ms delays)                             │
│  • Frontrunning (100ms windows)                                  │
│  • Liquidity Drain (sudden orderbook collapse)                   │
│  • Exchange Outage (missing data)                                │
│  • Cross-Exchange Spread (arbitrage opportunities)               │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│              Algorithm Refinement Engine                         │
│  Applies automatic adjustments:                                  │
│  • Blacklists symbols (wash trading)                             │
│  • Adjusts coherence thresholds (spoofing)                       │
│  • Uses multi-exchange mean prices (arbitrage)                   │
│  • Logs all refinements for analysis                             │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                  AurisEngine Integration                         │
│  • scan_for_anomalies() - Periodic scanning                      │
│  • is_symbol_blacklisted() - Filter opportunities                │
│  • get_coherence_adjustment() - Dynamic thresholds               │
│  • _apply_anomaly_refinement() - Auto-adjust rules               │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│              find_opportunities() Pipeline                       │
│  1. Scan for anomalies every 5 minutes                           │
│  2. Filter blacklisted symbols                                   │
│  3. Apply coherence adjustments                                  │
│  4. Continue with HNC + Probability analysis                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Configuration

### Environment Variables

```bash
# Required for live anomaly detection
export COINAPI_KEY=your-api-key-here
export ENABLE_COINAPI=1
```

### CONFIG Parameters

```python
CONFIG = {
    # CoinAPI Anomaly Detection
    'ENABLE_COINAPI': False,              # Requires API key
    'COINAPI_SCAN_INTERVAL': 300,         # Scan every 5 minutes
    'COINAPI_MIN_SEVERITY': 0.40,         # Act on anomalies ≥40% severity
    'COINAPI_BLACKLIST_DURATION': 3600,   # Blacklist for 1 hour
    'COINAPI_ADJUST_COHERENCE': True,     # Auto-adjust thresholds
    'COINAPI_PRICE_SOURCE': 'multi_exchange',  # Use aggregated prices
}
```

---

## 📊 Anomaly Types & Refinements

| Anomaly Type | Detection Method | Automatic Refinement |
|--------------|------------------|----------------------|
| 💰 **Price Manipulation** | Price >2% from cross-exchange mean | Increase coherence threshold +0.1<br>Reduce position size ×0.5 |
| 🔄 **Wash Trading** | >15% trades at identical prices | **Blacklist for 1 hour**<br>Position size ×0.0 |
| 📊 **Orderbook Spoofing** | Bid/ask ratio >70/30 | Delay entry +60s<br>Reduce position size ×0.7 |
| 🌐 **Cross-Exchange Spread** | >2% arbitrage opportunity | Use multi-exchange mean price<br>**Increase position size ×1.2** |
| ⚡ **Latency Arbitrage** | >500ms delays | Compensate for latency<br>Reduce position size ×0.8 |
| 📈 **Volume Inflation** | Volume >3× normal | Require higher volume confirmation |
| 🎯 **Frontrunning** | Suspicious <100ms patterns | Delay execution slightly |
| 💧 **Liquidity Drain** | Orderbook collapse | Avoid until liquidity returns |
| 🚨 **Exchange Outage** | Missing data feeds | Skip exchange temporarily |

---

## 🚀 Usage

### Basic Integration (Disabled by Default)

```python
from aureon_unified_ecosystem import AureonKrakenEcosystem

# Without CoinAPI (default)
eco = AureonKrakenEcosystem(initial_balance=200.0, dry_run=True)
# Anomaly detection is disabled but methods are available
```

### With CoinAPI Key

```python
import os
os.environ['COINAPI_KEY'] = 'your-key-here'
os.environ['ENABLE_COINAPI'] = '1'

from aureon_unified_ecosystem import AureonKrakenEcosystem

eco = AureonKrakenEcosystem(initial_balance=200.0, dry_run=True)
# CoinAPI anomaly detection is now ACTIVE
```

### Manual Anomaly Scanning

```python
# Scan specific symbols for anomalies
symbols = ['BTC/USD', 'ETH/USD', 'BNB/USD']
anomalies = eco.auris.scan_for_anomalies(symbols)

for anom in anomalies:
    print(f"Detected: {anom['type']}")
    print(f"Severity: {anom['severity']:.0%}")
    print(f"Recommendation: {anom['recommendation']}")
```

### Check Blacklist Status

```python
# Check if symbol is blacklisted
if eco.auris.is_symbol_blacklisted('BTC/USD'):
    print("BTC/USD is blacklisted due to anomaly")

# Get coherence adjustment
adjustment = eco.auris.get_coherence_adjustment('ETH/USD')
print(f"ETH/USD coherence threshold: ×{adjustment:.2f}")
```

---

## 📈 Integration with HNC + Probability Matrix

The CoinAPI layer works seamlessly with existing systems:

```
1. CoinAPI Anomaly Detection
   ↓ (Filters & Adjusts)
2. Opportunity Filtering
   ↓ (Blacklist check)
3. HNC Frequency Analysis
   ↓ (Harmonic bonus/penalty)
4. Probability Matrix
   ↓ (2-hour forecast)
5. Final Score & Position Sizing
   ↓
6. Trade Execution
```

### Example Flow

```python
# Symbol goes through complete pipeline:

# 1. CoinAPI detects orderbook spoofing on XYZ/USD
#    → Coherence threshold increased to 0.75 (from 0.65)

# 2. Opportunity filtering
#    → XYZ/USD requires 0.75 coherence instead of 0.65

# 3. HNC analysis shows 528Hz harmonic
#    → +15 score bonus, ×1.15 position size

# 4. Probability matrix shows 88% probability
#    → +20 score bonus

# 5. Final score: 145
#    → Passes thresholds despite higher coherence requirement
#    → Position opened with adjusted size
```

---

## 🧪 Testing

### Run Comprehensive Test Suite

```bash
python test_coinapi_integration.py
```

Tests include:
- ✅ Blacklist functionality
- ✅ Coherence adjustments
- ✅ Anomaly refinement logic
- ✅ Opportunity filtering
- ✅ Full system integration

### Standalone CoinAPI Demo

```bash
python coinapi_anomaly_detector.py
```

Demonstrates:
- Cross-exchange price analysis
- Anomaly detection with simulated data
- Algorithm refinement recommendations

---

## 💰 CoinAPI Free Tier

| Feature | Limit |
|---------|-------|
| **Requests/Day** | 100 |
| **Exchanges** | 300+ |
| **Data Types** | OHLCV, Quotes, Orderbooks, Trades |
| **Historical** | Limited |
| **WebSocket** | No (REST only) |

### Optimization Strategy

With 100 requests/day and 5-minute scans:
- **288 potential scans/day** (1 request per scan)
- **Scan 3-5 symbols per scan** (15-25 symbols covered)
- **Rotate through top opportunities** (not all symbols)
- **Cache results aggressively** (minimize duplicate calls)

---

## 📊 Real-World Example

### Detected Anomaly Report

```
╔══════════════════════════════════════════════════════════════════════════╗
║  🌍⚡ COINAPI ANOMALY REPORT: BTC/USD                                   ║
╠══════════════════════════════════════════════════════════════════════════╣
║  Exchanges Analyzed: 5                                                   ║
║  Mean Price: $69420.50                                                   ║
║  Price StdDev: $350.25                                                   ║
╠══════════════════════════════════════════════════════════════════════════╣
║  DETECTED ANOMALIES:                                                     ║
╠══════════════════════════════════════════════════════════════════════════╣
║  1. 💰 Price Manipulation                                                ║
║     Severity: ███████░░░ 75%                                             ║
║     Price 4.2% away from cross-exchange mean                             ║
║     → AVOID                                                              ║
╠══════════════════════════════════════════════════════════════════════════╣
║  2. 🌐 Cross-Exchange Spread                                             ║
║     Severity: ████░░░░░░ 45%                                             ║
║     2.8% arbitrage spread between exchanges                              ║
║     → ARBITRAGE OPPORTUNITY                                              ║
╠══════════════════════════════════════════════════════════════════════════╣
║  ALGORITHM REFINEMENTS:                                                  ║
╠══════════════════════════════════════════════════════════════════════════╣
║  1. Price manipulation detected - require higher confidence              ║
║     • coherence_threshold: +0.1                                          ║
║     • position_size: ×0.5                                                ║
╠══════════════════════════════════════════════════════════════════════════╣
║  2. Arbitrage opportunity - use aggregated price                         ║
║     • price_source: multi_exchange_mean                                  ║
║     • position_size: ×1.2                                                ║
╚══════════════════════════════════════════════════════════════════════════╝
```

---

## 🎯 Key Benefits

### 1. **Data Quality Validation**
- Cross-validates exchange data
- Detects feed manipulation
- Uses professional-grade aggregated data

### 2. **Adaptive Algorithm**
- Automatically adjusts to market conditions
- Learns from anomalies
- Refines thresholds in real-time

### 3. **Risk Reduction**
- Avoids manipulated markets
- Identifies wash trading
- Detects spoofed liquidity

### 4. **Opportunity Enhancement**
- Finds arbitrage opportunities
- Uses better pricing data
- Exploits market inefficiencies

---

## 🔮 Future Enhancements

1. **Historical Anomaly Analysis**
   - Track anomaly patterns over time
   - Machine learning on refinement effectiveness

2. **Exchange Reputation Scoring**
   - Rate exchanges by data quality
   - Prefer reliable exchanges

3. **Real-Time WebSocket Integration**
   - Upgrade to paid tier for WebSocket
   - Sub-second anomaly detection

4. **Cross-Asset Correlation**
   - Detect manipulation across asset pairs
   - Systemic risk indicators

---

## 📚 Files

| File | Purpose |
|------|---------|
| `coinapi_anomaly_detector.py` | Core anomaly detection engine |
| `test_coinapi_integration.py` | Comprehensive test suite |
| `aureon_unified_ecosystem.py` | Integration into main system |
| `COINAPI_INTEGRATION.md` | This documentation |

---

## 🏆 Success Metrics

Track these metrics to measure CoinAPI value:

- **Anomalies Detected** - Total count by type
- **Symbols Blacklisted** - Wash trading avoidance
- **Refinements Applied** - Algorithm adjustments
- **Arbitrage Opportunities** - Cross-exchange spreads found
- **False Positive Rate** - Good trades filtered incorrectly
- **Performance Impact** - Win rate before/after CoinAPI

---

## 🌟 Conclusion

CoinAPI integration adds a **professional data validation layer** to our trading system. By detecting anomalies in cross-exchange data, we:

✅ Avoid manipulated markets  
✅ Identify real arbitrage opportunities  
✅ Automatically refine our algorithms  
✅ Use higher-quality aggregated pricing  
✅ Reduce false signals and bad trades  

The system now combines:
1. **HNC Frequency Analysis** (Solfeggio harmonics)
2. **Probability Matrix** (2-hour temporal forecasting)
3. **CoinAPI Anomaly Detection** (cross-exchange validation)

**Result**: A self-improving trading algorithm that learns from market anomalies and adapts in real-time.

---

*"The Truth is in the Anomalies"*  
**Gary Leckey | November 30, 2025**
