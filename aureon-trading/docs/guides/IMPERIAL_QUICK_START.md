# 🌌 Imperial Predictability - Quick Start Guide

## Running the Demo

```bash
# Activate virtual environment
source .venv-1/bin/activate

# Run the Imperial demo
python hnc_imperial_predictability.py
```

## Using in Your Trading Code

### 1. Check Cosmic Status

```python
from aureon_unified_ecosystem import AurisEngine

# Initialize
cortex = AurisEngine()

# Get current cosmic state
cosmic = cortex.get_cosmic_status()
print(f"Phase: {cosmic['phase']}")
print(f"Coherence: {cosmic['coherence']:.2%}")
print(f"Distortion: {cosmic['distortion']:.3%}")
print(f"Torque: ×{cosmic['planetary_torque']:.2f}")
```

### 2. Check if Trading is Allowed

```python
# Check cosmic conditions
should_trade, reason = cortex.should_trade_imperial()

if should_trade:
    print(f"✅ Trading allowed: {reason}")
else:
    print(f"🛑 Trading halted: {reason}")
```

### 3. Get Prediction for a Symbol

```python
# Get imperial prediction
prediction = cortex.get_imperial_prediction(
    symbol='BTCGBP',
    price=75000,
    momentum=5.0  # 24h change %
)

print(f"Probability: {prediction['probability']:.1%}")
print(f"Action: {prediction['action']}")
print(f"Position Multiplier: ×{prediction['multiplier']:.2f}")
print(f"1H Signal: {prediction['1h_signal']}")
print(f"Cosmic Phase: {prediction['cosmic_phase']}")
```

### 4. Enhance Opportunities

```python
# Your opportunity from scanner
opportunity = {
    'symbol': 'BTCGBP',
    'price': 75000,
    'change24h': 5.2,
    'coherence': 0.85,
    'score': 100
}

# Enhance with Imperial
enhanced = cortex.enhance_opportunity_imperial(opportunity)

# Now has imperial metrics
imperial = enhanced['imperial']
print(f"Enhanced Score: {enhanced['score']}")
print(f"Imperial Probability: {imperial['probability']:.1%}")
print(f"Position Multiplier: ×{imperial['position_multiplier']:.2f}")
```

### 5. Get Position Size Modifier

```python
# Get dynamic position modifier
modifier = cortex.get_imperial_position_modifier(
    symbol='ETHGBP',
    momentum=3.1,
    price=2500
)

# Use in position sizing
base_size = 0.10  # 10% of capital
adjusted_size = base_size * modifier
print(f"Adjusted position: {adjusted_size:.1%} of capital")
```

## Configuration

### Enable/Disable Imperial

```python
# In environment or CONFIG
CONFIG['ENABLE_IMPERIAL'] = True  # or False

# Via environment variable
export ENABLE_IMPERIAL=1  # or 0
```

### Adjust Settings

```python
CONFIG['IMPERIAL_POSITION_WEIGHT'] = 0.35  # Weight in sizing (0-1)
CONFIG['IMPERIAL_MIN_COHERENCE'] = 0.50    # Min coherence to trade
CONFIG['IMPERIAL_DISTORTION_LIMIT'] = 0.15 # Max distortion threshold
CONFIG['IMPERIAL_COSMIC_BOOST'] = True     # Apply phase bonuses
```

## Interpreting Results

### Cosmic Phases

| Phase | Trading | Position Sizing |
|-------|---------|-----------------|
| 🌈 UNITY | ✅ Excellent | 1.5x boost |
| 🔵 COHERENCE | ✅ Good | 1.3x boost |
| 🟢 HARMONIC | ✅ Normal | 1.1x boost |
| 🟡 TRANSITION | ⚠️ Cautious | 1.0x normal |
| 🔴 DISTORTION | 🛑 Halted | Trading stopped |

### Position Multipliers

- **0.1x - 0.4x**: Extreme bearish / sell signal
- **0.5x - 0.7x**: Bearish / reduce size
- **0.8x - 1.0x**: Neutral / normal size
- **1.1x - 1.3x**: Bullish / increase size
- **1.4x - 1.5x**: Extreme bullish / max size

### Probability Thresholds

- **< 40%**: Low probability, reduce size or avoid
- **40-55%**: Neutral, normal sizing
- **55-65%**: Good probability, increase size
- **65-75%**: High probability, significant boost
- **> 75%**: Very high probability, max sizing

## Example: Complete Trading Flow

```python
from aureon_unified_ecosystem import AurisEngine

# Initialize
cortex = AurisEngine()

# 1. Update cosmic state (do once per minute)
cortex.update_cosmic_state({'vix': 18})

# 2. Check if we should trade
should_trade, reason = cortex.should_trade_imperial()
if not should_trade:
    print(f"Skipping trading: {reason}")
    exit()

# 3. Find opportunities (your existing scanner)
opportunities = find_trading_opportunities()

# 4. Enhance each with Imperial
enhanced_opps = []
for opp in opportunities:
    enhanced = cortex.enhance_opportunity_imperial(opp)
    enhanced_opps.append(enhanced)

# 5. Sort by enhanced score
enhanced_opps.sort(key=lambda x: x['score'], reverse=True)

# 6. Execute best opportunity
best = enhanced_opps[0]
imperial = best['imperial']

print(f"Trading {best['symbol']}")
print(f"  Probability: {imperial['probability']:.1%}")
print(f"  Action: {imperial['action']}")
print(f"  Position Multiplier: ×{imperial['position_multiplier']:.2f}")

# Position sizing already includes imperial modifier
# via calculate_position_size() in the ecosystem
```

## Monitoring

### Print Cosmic Dashboard

```python
# Get comprehensive status
if cortex.imperial:
    cortex.imperial.print_cosmic_dashboard()
```

### High Probability Opportunities

```python
# Get symbols with high probability forecasts
high_prob = cortex.imperial.engine.get_high_probability_opportunities(
    min_prob=0.65
)

for opp in high_prob:
    print(f"{opp['symbol']}: {opp['probability']:.1%} - {opp['action']}")
```

## Troubleshooting

### Imperial Not Available

If you see "Imperial Predictability not available":
```bash
# Check if file exists
ls hnc_imperial_predictability.py

# Try importing manually
python -c "from hnc_imperial_predictability import ImperialTradingIntegration"
```

### Distortion Phase Blocking Trades

Current date is in a distortion phase (Dec 1 @ 17% coherence). This will improve as we move toward:
- **Dec 7-8**: Grand Trine + Jupiter Cazimi (peak alignment)
- **Dec 21**: Winter Solstice (strong torque)

### Adjusting Thresholds

If Imperial is too conservative:
```python
CONFIG['IMPERIAL_MIN_COHERENCE'] = 0.30      # Lower threshold
CONFIG['IMPERIAL_DISTORTION_LIMIT'] = 0.25   # Higher tolerance
CONFIG['IMPERIAL_POSITION_WEIGHT'] = 0.20    # Reduce impact
```

## Advanced Features

### Custom Market Data

```python
# Update cosmic state with market data
market_data = {
    'vix': 18,           # Volatility index
    'btc_change': 5.2,   # BTC 24h change
    'sp500_change': 0.8, # S&P 500 change
    'dxy_change': -0.3,  # Dollar index change
}

cosmic_state = cortex.imperial.update_cosmic_state(market_data)
```

### Multi-Timeframe Analysis

```python
prediction = cortex.get_imperial_prediction('BTCGBP', 75000, 5.0)

# Access different timeframes
print(f"1H:  {prediction['1h_signal']} - {prediction['btc_forecast']:+.1f}%")
print(f"4H:  {prediction.get('4h_signal', 'N/A')}")
```

---

**🌌⚡ Happy Trading with Cosmic Synchronization! ⚡🌌**
