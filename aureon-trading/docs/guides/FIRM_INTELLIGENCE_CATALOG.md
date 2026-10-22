# 📊 Firm Intelligence Catalog System

## Overview

The **Firm Intelligence Catalog** is a real-time intelligence database that tracks major trading firms' activity across all markets. It provides:

- **24-hour movement history** - Every buy, sell, accumulation, distribution
- **Pattern recognition** - Repeating behavioral patterns (time-of-day, symbol preferences, strategies)
- **Market correlations** - Which firms lead markets, which follow
- **Probability predictions** - What firms will do next (direction, timing, symbols)
- **Success tracking** - Win rates, profit metrics, execution quality
- **Behavioral fingerprints** - Unique trading signatures per firm

**This gives us UNFAIR ADVANTAGE**: Know what they're doing BEFORE they do it.

---

## Architecture

```text
┌────────────────────────────────────────────────────────┐
│           FIRM INTELLIGENCE CATALOG                     │
│                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  MOVEMENTS  │  │   PATTERNS   │  │ CORRELATIONS │ │
│  │  (Real-time)│  │ (Recognition)│  │  (Predictive)│ │
│  └─────────────┘  └──────────────┘  └──────────────┘ │
│         │                 │                   │        │
│         └─────────────────┴───────────────────┘        │
│                           │                             │
│                    ┌──────▼──────┐                     │
│                    │  STATISTICS │                     │
│                    │  & PREDICTIONS                    │
│                    └─────────────┘                     │
└────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼──────┐   ┌────────▼────────┐  ┌──────▼─────┐
│ BOT SCANNER  │   │ COUNTER-INTEL   │  │  ORCA      │
│ (Detection)  │   │ (Strategy)      │  │ (Execution)│
└──────────────┘   └─────────────────┘  └────────────┘
```

### Integration Points

1. **Bot Shape Scanner** → Records firm movements when bots detected
2. **Counter-Intelligence** → Uses statistics for counter-strategy confidence boosting
3. **Orca Intelligence** → Derives whale signals from firm activity patterns
4. **Queen Hive Mind** → Accesses predictions for execution gates

---

## Data Structures

### FirmMovement

A single tracked trading action:

```python
@dataclass
class FirmMovement:
    firm_id: str                     # "citadel", "jane_street", etc.
    timestamp: float                 # Unix timestamp
    symbol: str                      # "BTC/USD", "ETH/USD", etc.
    activity_type: FirmActivityType  # BUY, SELL, ACCUMULATION, etc.
    volume_usd: float                # Trade size
    price: float                     # Execution price
    side: str                        # 'buy' or 'sell'
    confidence: float                # Attribution confidence (0-1)
    
    # Derived
    market_impact: float             # Price change caused (%)
    success_score: float             # Profitability
    pattern_match: Optional[str]     # Matched pattern name
    
    # Context
    market_regime: MarketRegime      # BULL, BEAR, SIDEWAYS, VOLATILE, QUIET
    time_of_day_hour: int            # 0-23
    day_of_week: int                 # 0-6
```

### FirmPattern

Recognized behavioral pattern:

```python
@dataclass
class FirmPattern:
    pattern_id: str                  # Unique identifier
    firm_id: str                     # Firm this pattern belongs to
    pattern_name: str                # "Active at 09:00", "BTC accumulation", etc.
    occurrences: int                 # How many times seen
    success_rate: float              # Win rate (0-1)
    avg_profit_pct: float            # Average profit %
    
    # Characteristics
    typical_volume_range: Tuple[float, float]
    typical_duration_seconds: float
    preferred_hours: List[int]       # [9, 10, 14] = active at 9am, 10am, 2pm
    preferred_symbols: List[str]     # ["BTC/USD", "ETH/USD"]
    market_regimes: List[MarketRegime]
    
    # Predictive
    next_move_probability: float     # Probability pattern repeats (0-1)
    confidence_score: float          # Confidence in pattern (0-1)
    last_seen: float                 # Last occurrence timestamp
```

### FirmStatistics

Aggregated statistics (24-hour window):

```python
@dataclass
class FirmStatistics:
    firm_id: str
    total_movements: int
    total_volume_usd: float
    avg_movement_size: float
    
    # Activity
    buys: int
    sells: int
    volume_bought: float
    volume_sold: float
    
    # Performance
    successful_moves: int
    failed_moves: int
    success_rate: float              # Win rate
    avg_profit_pct: float            # Average profit
    total_market_impact: float       # Cumulative impact
    
    # Behavioral
    most_active_hours: List[int]     # Top 3 hours
    most_active_symbols: List[str]   # Top 5 symbols
    dominant_activity_type: FirmActivityType
    
    # Predictions
    next_24h_activity_probability: float  # 0-1
    predicted_direction: str         # 'bullish', 'bearish', 'neutral'
    confidence: float                # Prediction confidence
```

---

## Key Methods

### Recording Data

```python
from aureon_firm_intelligence_catalog import get_firm_catalog

catalog = get_firm_catalog()

# Record a firm movement
movement = catalog.record_movement(
    firm_id='citadel',
    symbol='BTC/USD',
    side='buy',
    volume_usd=2_500_000,
    price=95000,
    confidence=0.85  # Attribution confidence
)
```

### Querying Statistics

```python
# Get 24-hour statistics
stats = catalog.compute_statistics('citadel')

print(f"Movements: {stats.total_movements}")
print(f"Volume: ${stats.total_volume_usd:,.0f}")
print(f"Success rate: {stats.success_rate:.0%}")
print(f"Predicted direction: {stats.predicted_direction}")
print(f"Next 24h probability: {stats.next_24h_activity_probability:.0%}")
```

### Pattern Recognition Queries

```python
# Recognize behavioral patterns
patterns = catalog.recognize_patterns('citadel', min_occurrences=3)

for pattern in patterns:
    print(f"Pattern: {pattern.pattern_name}")
    print(f"  Occurrences: {pattern.occurrences}")
    print(f"  Success rate: {pattern.success_rate:.0%}")
    print(f"  Next probability: {pattern.next_move_probability:.0%}")
```

### Comprehensive Summary

```python
# Get full intelligence summary
summary = catalog.get_firm_summary('citadel')

# Access components
stats = summary['statistics']
patterns = summary['patterns']
recent_movements = summary['recent_movements']
prediction = summary['prediction']

print(f"Prediction: {prediction['reasoning']}")
print(f"Confidence: {prediction['confidence']:.0%}")
```

### Market Leaders

```python
# Get top firms by volume in a market
leaders = catalog.get_market_leaders('BTC/USD', top_n=5)

for firm_id, volume in leaders:
    print(f"{firm_id}: ${volume:,.0f}")
```

---

## CLI Usage

The catalog comes with a powerful CLI tool:

```bash
# Show catalog status
python firm_catalog_cli.py status

# List all active firms
python firm_catalog_cli.py list

# Get detailed firm analysis
python firm_catalog_cli.py firm citadel

# Show market leaders for a symbol
python firm_catalog_cli.py leaders BTC/USD

# Show recognized patterns
python firm_catalog_cli.py patterns citadel

# Get prediction
python firm_catalog_cli.py predict jane_street

# Export to JSON
python firm_catalog_cli.py export citadel --output citadel_intel.json

# Live watch (refreshes every 3s)
python firm_catalog_cli.py watch citadel --interval 3
```

### CLI Examples

**Status:**

```text
📊 FIRM INTELLIGENCE CATALOG STATUS
============================================================
Total firms tracked: 15
Active firms (24h):  8
Total movements:     247
Total patterns:      34
Lookback period:     24 hours
============================================================
```

**Firm Summary:**

```text
📊 FIRM INTELLIGENCE: CITADEL
============================================================

📈 STATISTICS (24h)
  Total movements:     42
  Total volume:        $127.5M
  Avg movement size:   $3.04M
  Buy/Sell ratio:      28/14
  Success rate:        67%
  Avg profit:          0.34%

🎯 BEHAVIORAL PATTERNS
  Dominant activity:   ACCUMULATION
  Active hours:        09:00, 10:00, 14:00
  Preferred symbols:   BTC/USD, ETH/USD, SOL/USD

🔍 RECOGNIZED PATTERNS (3)
  1. Active at 09:00
     Occurrences: 12 | Last seen: 15m ago
  2. BTC/USD accumulation
     Occurrences: 8 | Last seen: 2h ago
  3. ETH/USD balanced
     Occurrences: 6 | Last seen: 4h ago

🔮 PREDICTION
    Next 24h activity:   85% probability
    Predicted direction: BULLISH
    Confidence:          72%
    Reasoning:           High activity probability (85%) | Bias: bullish | 3 patterns recognized | Focus on: BTC/USD, ETH/USD
```

---

## Integration Examples

### With Counter-Intelligence

```python
from aureon_firm_intelligence_catalog import get_firm_catalog
from aureon_queen_counter_intelligence import QueenCounterIntelligence

catalog = get_firm_catalog()
counter_intel = QueenCounterIntelligence()

# Counter-intel automatically uses catalog statistics
signal = counter_intel.analyze_firm_for_counter_opportunity(
    firm_id='citadel',
    market_data={
        'symbol': 'BTC/USD',
        'price': 95000,
        'volume': 2_500_000,
        'spread': 0.0005
    }
)

if signal:
    print(f"Counter opportunity: {signal.counter_strategy}")
    print(f"Confidence: {signal.confidence:.0%}")
    print(f"Expected profit: {signal.expected_profit_pips} pips")
```

### With Bot Scanner

```python
from aureon_bot_shape_scanner import BotShapeScanner
from aureon_firm_intelligence_catalog import get_firm_catalog

scanner = BotShapeScanner(['BTCUSDT', 'ETHUSDT'])
catalog = get_firm_catalog()

# Scanner automatically records firm movements to catalog
# when bots are detected and attributed to firms
scanner.start()

# Query catalog later for intelligence
stats = catalog.compute_statistics('citadel')
print(f"Citadel activity: {stats.total_movements} movements")
```

### With Orca Intelligence

```python
from aureon_orca_intelligence import OrcaIntelligence
from aureon_firm_intelligence_catalog import get_firm_catalog

orca = OrcaIntelligence()
catalog = get_firm_catalog()

# Orca uses catalog predictions for whale signal derivation
summary = catalog.get_firm_summary('citadel')

if summary['prediction']['next_24h_probability'] > 0.8:
    # High probability firm is about to move
    # Create derived whale signal
    whale_signal = orca.create_whale_signal_from_firm_intel(summary)
```

---

## Prediction Algorithm

### Activity Probability

Predicts likelihood of activity in next 24 hours:

```python
def predict_activity_probability(recent_movements):
    """
    Based on:
    1. Historical activity frequency (avg interval between movements)
    2. Time since last movement
    3. Consistency of pattern
    
    Returns: 0.0 to 1.0
    """
    avg_interval = calculate_average_interval(recent_movements)
    hours_since_last = hours_since_last_movement()
    
    if avg_interval < 1h and hours_since_last < 6h:
        return 0.85  # Very active, recent
    elif avg_interval < 2h and hours_since_last < 12h:
        return 0.65  # Moderately active
    else:
        return 0.45  # Lower probability
```

### Direction Prediction

Predicts likely next direction (bullish/bearish/neutral):

```python
def predict_direction(recent_movements):
    """
    Based on:
    1. Buy/Sell volume ratio
    2. Recent bias (last 5 movements)
    3. Pattern consistency
    
    Returns: 'bullish', 'bearish', or 'neutral'
    """
    recent_5 = last_5_movements()
    
    buy_volume = sum(buy volumes)
    sell_volume = sum(sell volumes)
    
    if buy_volume > sell_volume * 1.5:
        return 'bullish'
    elif sell_volume > buy_volume * 1.5:
        return 'bearish'
    else:
        return 'neutral'
```

### Confidence Calculation

```python
def calculate_prediction_confidence(recent_movements):
    """
    Based on:
    1. Data volume (more data = higher confidence)
    2. Pattern consistency (repeating behaviors)
    3. Success rate (profitable outcomes)
    
    Returns: 0.0 to 1.0
    """
    if len(recent_movements) < 5:
        return 0.3  # Low confidence with little data
    
    if len(recent_movements) >= 10:
        # Check consistency of last 10 movements
        consistency = calculate_consistency(recent_movements[-10:])
        return 0.5 + (consistency * 0.5)  # 0.5 to 1.0 range
    
    return 0.5  # Medium confidence
```

---

## Pattern Recognition

### Time-of-Day Patterns

Detects if firm is consistently active at specific hours:

```python
# Example: Citadel active at 9am, 10am, 2pm
pattern = FirmPattern(
    pattern_name="Active at 09:00",
    preferred_hours=[9],
    occurrences=12,
    success_rate=0.75
)
```

### Symbol-Specific Patterns

Detects accumulation/distribution patterns per symbol:

```python
# Example: Jane Street accumulating BTC
pattern = FirmPattern(
    pattern_name="BTC/USD accumulation",
    preferred_symbols=["BTC/USD"],
    occurrences=8,
    success_rate=0.68
)
```

### Activity Type Patterns

Detects dominant trading behaviors:

```python
# Example: Two Sigma market making
pattern = FirmPattern(
    pattern_name="ETH market making",
    preferred_symbols=["ETH/USD"],
    activity_type=FirmActivityType.MARKET_MAKING,
    occurrences=15,
    success_rate=0.72
)
```

---

## State Persistence

The catalog automatically persists state to:

- `firm_intelligence_catalog_state.json`

State includes:

- All movements from last 24 hours
- All recognized patterns
- Metadata (last update time, etc.)

**Atomic writes**: Uses `.tmp` file → rename pattern to prevent corruption.

---

## Performance Considerations

### Memory Management

- Movements limited to 1000 per firm (deque with maxlen)
- Automatic cleanup of movements older than lookback period
- Only recent 24h persisted to disk

### Computation Optimization

- Statistics cached after computation
- Pattern recognition only on-demand
- Correlations updated incrementally

### Scalability

- Handles 100+ firms simultaneously
- Processes 1000s of movements/hour
- Sub-millisecond query times for cached data

---

## Counter-Intelligence Integration

The catalog boosts counter-intelligence confidence:

```python
# In counter-intelligence analysis:
if catalog_available:
    firm_summary = catalog.get_firm_summary(firm_id)
    
    # Boost confidence if firm is active and predictable
    if prediction['next_24h_probability'] > 0.7 and prediction['confidence'] > 0.7:
        confidence += 0.1  # +10% confidence boost
    
    # Boost if predicted direction aligns with counter-strategy
    if direction_aligns_with_counter:
        confidence += 0.05  # +5% confidence boost
```

This makes counter-trades more confident when:

1. Firm is actively trading (recent movements)
2. Patterns are clear and consistent
3. Predictions align with our counter-strategy

---

## Future Enhancements

### Planned Features

1. **Market Correlation Tracking**
   - Measure how firm activity correlates with price movements
   - Identify lead/lag relationships
   - Predictive power scoring

2. **Cross-Market Analysis**
   - Track firms across multiple exchanges
   - Identify arbitrage patterns
   - Detect coordinated attacks

3. **Machine Learning Integration**
   - Neural network for pattern recognition
   - Deep learning for price impact prediction
   - Reinforcement learning for optimal counter-timing

4. **Real-Time Alerting**
   - Alert when high-confidence patterns detected
   - Notification when firm activity spikes
   - Warning when prediction confidence drops

5. **Historical Backtesting**
   - Test pattern recognition on historical data
   - Validate prediction accuracy
   - Optimize thresholds

---

## Best Practices

### Data Quality

1. **Attribution Confidence**: Only record movements with confidence ≥ 0.5
2. **Volume Validation**: Verify volume matches market data
3. **Timestamp Accuracy**: Use precise timestamps for timing analysis

### Pattern Recognition Best Practices

1. **Minimum Occurrences**: Require ≥3 occurrences before recognizing pattern
2. **Recency Weighting**: Prioritize recent patterns over old ones
3. **Success Filtering**: Only track patterns with success rate > 50%

### Prediction Usage

1. **Confidence Thresholds**: Only act on predictions with confidence ≥ 0.7
2. **Cross-Validation**: Verify predictions against multiple data sources
3. **Time Decay**: Reduce confidence as time passes since last movement

### Integration

1. **Graceful Degradation**: System works without catalog (optional dependency)
2. **Error Handling**: Catch and log all exceptions, never crash
3. **Performance**: Query catalog async to avoid blocking

---

## Troubleshooting

### No Movements Recorded

**Symptom**: `get_all_active_firms()` returns empty list

**Causes**:

- No firms attributed (attribution engine not working)
- All movements older than 24h (expired)
- Catalog not receiving data from bot scanner

**Fix**:

```python
# Check if bot scanner is feeding catalog
from aureon_bot_shape_scanner import BotShapeScanner
scanner = BotShapeScanner(['BTCUSDT'])
print(f"Catalog available: {scanner.firm_catalog is not None}")

# Manually record test movement
catalog.record_movement('test_firm', 'BTC/USD', 'buy', 1000000, 95000)
```

### Low Prediction Confidence

**Symptom**: All predictions have confidence < 0.5

**Causes**:

- Insufficient data (< 5 movements)
- Inconsistent patterns (no clear behaviors)
- Recent firm activity is erratic

**Fix**:

- Wait for more data to accumulate
- Lower recognition thresholds temporarily
- Check if firm changed strategy recently

### Patterns Not Recognized

**Symptom**: `recognize_patterns()` returns empty list

**Causes**:

- Occurrences < min_occurrences threshold
- Movements too sparse (no clustering)
- Patterns genuinely absent

**Fix**:

```python
# Lower threshold temporarily
patterns = catalog.recognize_patterns('citadel', min_occurrences=2)

# Check raw movements
movements = catalog._get_recent_movements('citadel')
print(f"Total movements: {len(movements)}")
```

---

## API Reference

See code docstrings in `aureon_firm_intelligence_catalog.py` for complete API reference.

---

**Built with ❤️ by Gary Leckey | January 2026**
**"Know thy enemy. Beat thy enemy."**
