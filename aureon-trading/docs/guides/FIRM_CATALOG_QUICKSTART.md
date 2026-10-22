# 🚀 Firm Intelligence Catalog - Quick Start

## What Is This?

**Real-time intelligence database** tracking major trading firms (Citadel, Jane Street, Two Sigma, etc.):

- Records every movement (buys, sells, volumes)
- Recognizes behavioral patterns
- Predicts next moves
- Integrates with counter-intelligence

**Goal**: Beat them at their own game by knowing what they'll do BEFORE they do it.

---

## 5-Minute Setup

### 1. Verify Installation

```bash
cd /workspaces/aureon-trading
python3 aureon_firm_intelligence_catalog.py
```text

You should see:

```text
📊 FIRM INTELLIGENCE CATALOG TEST 📊
✅ Firm Intelligence Catalog ready
```text

### 2. Test CLI

```bash
# Check status
python3 firm_catalog_cli.py status

# List active firms
python3 firm_catalog_cli.py list
```

### 3. Simulate Some Data

```python
from aureon_firm_intelligence_catalog import get_firm_catalog

catalog = get_firm_catalog()

# Record Citadel buying BTC
catalog.record_movement('citadel', 'BTC/USD', 'buy', 2_500_000, 95000, confidence=0.85)
catalog.record_movement('citadel', 'BTC/USD', 'buy', 1_800_000, 95100, confidence=0.88)
catalog.record_movement('citadel', 'BTC/USD', 'buy', 3_000_000, 95200, confidence=0.90)

# Get statistics
stats = catalog.compute_statistics('citadel')
print(f"Movements: {stats.total_movements}")
print(f"Predicted: {stats.predicted_direction} ({stats.next_24h_activity_probability:.0%})")
```

---

## Common Use Cases

### Use Case 1: Check What Citadel Is Doing

```bash
python3 firm_catalog_cli.py firm citadel
```

**Output:**

```text
📊 FIRM INTELLIGENCE: CITADEL
============================================================

📈 STATISTICS (24h)
  Total movements:     42
  Total volume:        $127.5M
  Predicted direction: BULLISH

🔮 PREDICTION
  Next 24h activity:   85% probability
  Confidence:          72%
```

### Use Case 2: Find Market Leaders

```bash
python3 firm_catalog_cli.py leaders BTC/USD
```

**Output:**

```text
📊 MARKET LEADERS: BTC/USD
============================================================
 1. citadel              $127.5M ████████████ 45.2%
 2. jane_street          $82.3M  ████████ 29.1%
 3. two_sigma            $45.1M  ████ 16.0%
```

### Use Case 3: Get Prediction

```bash
python3 firm_catalog_cli.py predict jane_street
```

**Output:**

```text
🔮 PREDICTION: JANE_STREET
============================================================

Next 24h Activity:  75% probability
Predicted Direction: BEARISH
Confidence Level:    68%

🟡 Confidence: MEDIUM

📋 Reasoning:
   High activity probability (75%) | Bias: bearish | 2 patterns recognized
```

### Use Case 4: Live Watching

```bash
# Refresh every 3 seconds
python3 firm_catalog_cli.py watch citadel --interval 3
```

**Output (updates live):**

```text
📊 LIVE WATCH: CITADEL
Updated: 2026-01-17 14:30:15
============================================================

📈 REAL-TIME STATS
  Movements (24h): 42
  Volume:          $127.5M
  Last activity:   2m ago

📝 RECENT ACTIVITY (Last 5)
  🟢 BTC/USD BUY $3.0M @ $95200 (2m ago)
  🟢 BTC/USD BUY $1.8M @ $95100 (5m ago)
  🔴 ETH/USD SELL $1.2M @ $3200 (8m ago)
```

---

## Integration with Counter-Intelligence

The catalog **automatically boosts counter-intelligence confidence**:

```python
from aureon_queen_counter_intelligence import QueenCounterIntelligence

counter_intel = QueenCounterIntelligence()

# Counter-intel uses catalog behind the scenes
signal = counter_intel.analyze_firm_for_counter_opportunity(
    firm_id='citadel',
    market_data={'symbol': 'BTC/USD', 'price': 95000}
)

# If catalog shows:
# - Citadel is very active (85% probability)
# - Predicted direction is bullish
# - Patterns are consistent
#
# Then counter-intel confidence gets +10-15% boost!
```

---

## Integration with Bot Scanner

The bot scanner **automatically records to catalog**:

```python
from aureon_bot_shape_scanner import BotShapeScanner

scanner = BotShapeScanner(['BTCUSDT', 'ETHUSDT'])

# Scanner detects bots → attributes to firms → records in catalog
scanner.start()

# Later, query catalog for intelligence
from aureon_firm_intelligence_catalog import get_firm_catalog
catalog = get_firm_catalog()

summary = catalog.get_firm_summary('citadel')
print(f"Citadel activity: {summary['statistics']['total_movements']} movements")
```

**Flow:**

```text
Bot Detected → Firm Attribution → Catalog Recording → Intelligence → Counter-Strategy
```

---

## Understanding Predictions

### Activity Probability

**What it means**: Likelihood firm will trade in next 24 hours

- **85%+**: Very active, expect more trades soon
- **65-85%**: Moderately active
- **45-65%**: Lower activity expected
- **< 45%**: Likely quiet

**Use**: Plan counter-trades around high-probability windows

### Direction Prediction

**What it means**: Expected bias (bullish/bearish/neutral)

- **Bullish**: More buying than selling recently
- **Bearish**: More selling than buying
- **Neutral**: Balanced or unclear

**Use**: Counter-trade against predicted direction (if firm is bullish, we go bearish)

### Confidence Score

**What it means**: How reliable the prediction is

- **> 70%**: High confidence (solid data, clear patterns)
- **50-70%**: Medium confidence (some data, some patterns)
- **< 50%**: Low confidence (sparse data, unclear patterns)

**Use**: Only act on predictions with confidence ≥ 70%

---

## Understanding Patterns

### Time-of-Day Patterns

**Example**: "Active at 09:00"

**Meaning**: Firm consistently trades around 9am

**Use**: Set up counter-trades at 8:55am to front-run them

### Symbol-Specific Patterns

**Example**: "BTC/USD accumulation"

**Meaning**: Firm is consistently buying BTC over time

**Use**: Front-run their next BTC buy with our own buy, sell after they push price up

### Activity Type Patterns

**Example**: "ETH market making"

**Meaning**: Firm provides liquidity (buy & sell) on ETH

**Use**: Trade against their liquidity, exploit their spreads

---

## Data Flow Architecture

```text
┌─────────────────────────────────────────────────────────┐
│                  MARKET DATA FEEDS                       │
│           (Binance, Kraken, Alpaca, etc.)               │
└─────────────────┬───────────────────────────────────────┘
                  │
         ┌────────▼────────┐
         │  BOT SCANNER    │
         │  (Detects bots) │
         └────────┬────────┘
                  │
         ┌────────▼────────────┐
         │  FIRM ATTRIBUTION   │
         │  (Identifies firms) │
         └────────┬────────────┘
                  │
         ┌────────▼─────────────┐
         │  FIRM CATALOG        │
         │  (Records movements) │
         └────────┬─────────────┘
                  │
       ┌──────────┴──────────┐
       │                     │
┌──────▼──────┐    ┌─────────▼─────────┐
│ PATTERNS    │    │ PREDICTIONS       │
│ (Recognize) │    │ (Forecast)        │
└──────┬──────┘    └─────────┬─────────┘
       │                     │
       └──────────┬──────────┘
                  │
       ┌──────────▼───────────┐
       │ COUNTER-INTELLIGENCE │
       │ (Strategy selection) │
       └──────────┬───────────┘
                  │
         ┌────────▼────────┐
         │  ORCA / QUEEN   │
         │  (Execution)    │
         └─────────────────┘
```

---

## CLI Command Cheat Sheet

```bash
# Status
python3 firm_catalog_cli.py status

# List all firms
python3 firm_catalog_cli.py list

# Detailed firm analysis
python3 firm_catalog_cli.py firm <firm_id>

# Market leaders
python3 firm_catalog_cli.py leaders <symbol>

# Patterns
python3 firm_catalog_cli.py patterns <firm_id>

# Prediction
python3 firm_catalog_cli.py predict <firm_id>

# Export to JSON
python3 firm_catalog_cli.py export <firm_id> --output <file>

# Live watch
python3 firm_catalog_cli.py watch <firm_id> --interval <seconds>
```

---

## Programmatic API Cheat Sheet

```python
from aureon_firm_intelligence_catalog import get_firm_catalog

catalog = get_firm_catalog()

# Record movement
catalog.record_movement(firm_id, symbol, side, volume_usd, price, confidence)

# Get statistics
stats = catalog.compute_statistics(firm_id)

# Recognize patterns
patterns = catalog.recognize_patterns(firm_id, min_occurrences=3)

# Get full summary
summary = catalog.get_firm_summary(firm_id)

# Get market leaders
leaders = catalog.get_market_leaders(symbol, top_n=5)

# Get all active firms
active_firms = catalog.get_all_active_firms()

# Get status
status = catalog.get_status()
```

---

## Firm IDs

**Supported firms** (add more in firm database):

- `citadel` - Citadel Securities
- `jane_street` - Jane Street
- `two_sigma` - Two Sigma
- `hudson_river_trading` (or `hrt`) - Hudson River Trading
- `jump_trading` - Jump Trading
- `virtu` - Virtu Financial
- `tower_research` - Tower Research
- `optiver` - Optiver
- `imc` - IMC Trading
- `sig` (or `susquehanna`) - Susquehanna (SIG)
- `drw` - DRW Trading
- `renaissance_tech` (or `rentech`) - Renaissance Technologies
- `de_shaw` - D.E. Shaw
- `millennium` - Millennium Management
- `balyasny` - Balyasny Asset Management

---

## Troubleshooting

### "No active firms"

**Cause**: No data recorded yet

**Fix**:

1. Make sure bot scanner is running
2. Or manually record test data:

```python
catalog.record_movement('citadel', 'BTC/USD', 'buy', 1000000, 95000)
```

### "Low confidence predictions"

**Cause**: Insufficient data (< 5 movements)

**Fix**: Wait for more data to accumulate, or lower thresholds

### "No patterns recognized"

**Cause**: Not enough repeated behaviors

**Fix**: Lower `min_occurrences` threshold:

```python
patterns = catalog.recognize_patterns('citadel', min_occurrences=2)
```

---

## What's Next?

1. **Start bot scanner** to feed live data
2. **Watch predictions** improve as data accumulates
3. **Use counter-intelligence** with catalog-boosted confidence
4. **Monitor results** via CLI watch command
5. **Export data** for external analysis

---

## Performance Tips

- **Memory**: Catalog stores max 1000 movements per firm
- **Disk**: State auto-saves to `firm_intelligence_catalog_state.json`
- **Speed**: Sub-millisecond queries for cached statistics
- **Scalability**: Handles 100+ firms, 1000s movements/hour

---

## Advanced Usage

### Custom Pattern Recognition

```python
# Override default pattern recognition
catalog.patterns['citadel'] = [
    FirmPattern(
        pattern_id='custom_pattern',
        firm_id='citadel',
        pattern_name='Morning accumulation',
        preferred_hours=[9, 10],
        preferred_symbols=['BTC/USD'],
        occurrences=15,
        success_rate=0.75
    )
]
```

### Export All Data

```bash
# Export all firms
for firm in $(python3 -c "from aureon_firm_intelligence_catalog import get_firm_catalog; print(' '.join(get_firm_catalog().get_all_active_firms()))"); do
    python3 firm_catalog_cli.py export $firm --output "export_${firm}.json"
done
```

### Integration Testing

```python
# Test full integration
from aureon_firm_intelligence_catalog import get_firm_catalog
from aureon_queen_counter_intelligence import QueenCounterIntelligence

catalog = get_firm_catalog()
counter = QueenCounterIntelligence()

# Simulate firm activity
for i in range(10):
    catalog.record_movement('citadel', 'BTC/USD', 'buy', 2_000_000, 95000 + i*100)

# Check if counter-intel gets boosted confidence
signal = counter.analyze_firm_for_counter_opportunity(
    'citadel',
    {'symbol': 'BTC/USD', 'price': 95000}
)

assert signal.confidence > 0.8, "Catalog should boost confidence"
print("✅ Integration test passed!")
```

---

Built with ❤️ by Gary Leckey | January 2026

"The best defense is a good offense. The best offense is perfect intelligence."
