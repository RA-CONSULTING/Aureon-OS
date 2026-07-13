# Aureon Trading System - Copilot Instructions

## Big picture (core pipeline)
- **Ecosystem → Scanner → Queen Hive**: feed layer produces “reality branches”, scanner runs 3-pass validation, Queen executes only on **4th confirmation**. Key files: `aureon_unified_ecosystem.py`, `aureon_probability_nexus.py`, `aureon_queen_hive_mind.py`, `micro_profit_labyrinth.py`.
- **Stargate Protocol** (timeline anchoring) integrates quantum mirror scans and 7‑day validation persistence: `aureon_stargate_protocol.py`, `aureon_quantum_mirror_scanner.py`, `aureon_timeline_anchor_validator.py` with `7day_pending_validations.json` and `7day_anchored_timelines.json`.
- **Thought Bus** is the cross-module event mesh (`aureon_thought_bus.py`). Always check `THOUGHT_BUS_AVAILABLE` before emitting/subscribing.

## Critical workflows (discoverable commands)
- Local dry-run execution: `python micro_profit_labyrinth.py --dry-run`.
- Health checks: `python check_system_logs.py` and `python comprehensive_diagnostic.py`.
- Balance/connectivity: `python check_all_balances.py` and `python verify_platform_connectivity.py`.
- Production container: see production README for Docker build/run and monitoring ports (UI 8888, API 8889, metrics 9090).

## Project-specific conventions
- **Real data only**: never use simulated prices/balances. If APIs are rate-limited, read the persisted state files instead (e.g., `aureon_kraken_state.json`).
- **Batten Matrix rule**: never execute on pass 1–3; only after 4th pass with coherence/lambda checks.
- **Windows UTF‑8 wrapper** must be at the top of every `.py` file (see existing files for the exact block).
- **Dataclasses for structured data**: define as `@dataclass`, serialize to JSON, and keep schemas stable across modules.
- **Sacred constants**: use centralized values (e.g., Schumann 7.83 Hz, $\phi$) instead of hardcoding.
- **Atomic JSON writes**: write temp file then rename to avoid corrupted state.

## CRITICAL AGENT RULES - READ FIRST!

### 🚫 NO NEW PYTHON FILES
- **ALWAYS search the repo first** before creating any new file
- Use `grep_search`, `file_search`, or `semantic_search` to find existing implementations
- The codebase already has 200+ modules - the solution likely exists
- Extend existing files rather than creating new ones
- If you must create a new file, explain WHY no existing file can be extended

### 🚫 NO SIMULATION DATA - REAL DATA ONLY
- **NEVER use fake/mock/simulated prices or balances**
- **NEVER generate random test data**
- Fetch REAL data from:
  - Exchange APIs (Kraken, Binance, Alpaca, Capital.com)
  - Open source feeds (CoinGecko, Yahoo Finance, etc.)
  - Persisted state files (`*_state.json`, `cost_basis_history.json`)
- If an API is rate-limited, use the **cached real data** from state files
- If no real data available, STOP and inform the user - do not invent data

### ✅ DATA SOURCES FOR REAL MARKET DATA
```python
# Open source price feeds (no API key needed):
# - CoinGecko: https://api.coingecko.com/api/v3/simple/price
# - Binance public: https://api.binance.com/api/v3/ticker/price
# - Kraken public: https://api.kraken.com/0/public/Ticker

# Persisted state files with real data:
# - cost_basis_history.json (247 positions)
# - aureon_kraken_state.json
# - alpaca_truth_tracker_state.json
# - elephant_memory.json
```

## Integration points
- Exchange clients share a common surface (`get_balance`, `get_ticker`, `execute_trade`) in `kraken_client.py`, `binance_client.py`, `alpaca_client.py`.
- Optional components: Windows launcher (see aureon_launcher/README.md) and local sensor WS server (server/README.md) that feeds Schumann/biometrics into the UI.

## Useful file map (start here)
- Pipeline: `aureon_unified_ecosystem.py`, `aureon_probability_nexus.py`, `aureon_queen_hive_mind.py`, `micro_profit_labyrinth.py`
- Profit gate equation: `adaptive_prime_profit_gate.py`
- State: `active_position.json`, `7day_*` files, `elephant_*.json`, `barter_graph_cache.json`
| **Timeline Anchoring** | `aureon_timeline_anchor_validator.py` |
| State files | `*.json` in repo root |

---

## Common Development Patterns

### Implementing a New Validation System
```python
# 1. Define dataclass for validation result
@dataclass
class NewValidationResult:
    symbol: str
    probability: float  # 0-1
    confidence: float
    reasoning: str

# 2. Create validator function
async def new_validation_pass(branch: Dict) -> float:
    """Validation pass N for Batten Matrix."""
    features = extract_features(branch)
    score = compute_validation_logic(features)
    return clip(score, 0.0, 1.0)

# 3. Integrate into probability nexus
# In aureon_probability_nexus.py:
p1 = await harmonic_validation(branch)
p2 = await coherence_validation(branch)
p3 = await new_validation_pass(branch)  # <-- Add here

# 4. Update coherence calculation
coherence = 1 - (max(p1, p2, p3) - min(p1, p2, p3))
```

### Adding a New Exchange Client
```python
# 1. Create client file: {exchange}_client.py
class NewExchangeClient:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
    
    def get_balance(self) -> Dict[str, float]:
        """Return {asset: amount}"""
        pass
    
    def get_ticker(self, symbol: str) -> Dict:
        """Return {bid, ask, last, timestamp}"""
        pass
    
    def execute_trade(self, symbol: str, side: str, quantity: float) -> Dict:
        """Execute trade, return order result"""
        pass

# 2. Add fee profile to adaptive_prime_profit_gate.py
DEFAULT_FEE_PROFILES = {
    'newexchange': {
        'maker': 0.001,  # 0.1%
        'taker': 0.0015,  # 0.15%
        'spread': 0.0005  # 0.05%
    }
}

# 3. Register in micro_profit_labyrinth.py turn rotation
exchanges = ["kraken", "binance", "alpaca", "newexchange"]
```

### Logging Best Practices
```python
import logging
logger = logging.getLogger(__name__)

# Structured logging with context
logger.info("Branch validation complete", extra={
    "branch_id": branch_id,
    "symbol": symbol,
    "coherence": coherence,
    "lambda": lambda_val,
    "pass_count": 3,
    "ready_for_4th": ready
})

# Error handling with Queen immune system
try:
    result = execute_trade(symbol, side, quantity)
except Exception as e:
    logger.error(f"Trade execution failed: {e}", exc_info=True)
    if hasattr(self, 'immune_system'):
        self.immune_system.handle_error('execution', e)
```

### Async/Await Pattern (Market Data)
```python
import asyncio
from typing import List, Dict

async def fetch_multi_exchange_data(symbols: List[str]) -> Dict:
    """Fetch data from multiple exchanges in parallel."""
    tasks = [
        fetch_kraken(symbols),
        fetch_binance(symbols),
        fetch_alpaca(symbols)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return merge_results(results)

# Usage
async def main():
    data = await fetch_multi_exchange_data(["BTC/USD", "ETH/USD"])
    # Process data...
```

---

## Troubleshooting Guide

### High Drift / Low Lambda Stability
**Symptom**: Execution rejected with "drift_too_high"  
**Cause**: Time between scan and 4th decision exceeded stability threshold  
**Fix**: 
- Reduce validation latency (parallelize passes)
- Increase drift decay constant α in lambda calculation
- Check network/API latency to exchanges

### Low Coherence Scores
**Symptom**: Validations (p₁, p₂, p₃) widely disagree  
**Cause**: Validators seeing different market states  
**Fix**:
- Synchronize data timestamps across validators
- Check if one validator is lagging (stale data)
- Investigate if market is genuinely volatile (no fix—wait for clarity)

### 4th Decision Never Triggers
**Symptom**: Branches stuck in `7day_pending_validations.json`  
**Cause**: Score S = p̄ · P · C · Λ below threshold  
**Debug**:
```bash
# Check pending validations
jq '.[] | {symbol, coherence, lambda, score}' 7day_pending_validations.json

# Lower threshold temporarily (TEST ONLY)
# In aureon_probability_nexus.py:
BRANCH_CONFIDENCE_THRESHOLD = 0.5  # Was 0.618 (golden ratio)
```

### Exchange API Rate Limits
**Symptom**: 429 errors from exchange  
**Cause**: Too many requests in turn-based loop  
**Fix**:
- Increase sleep interval in `micro_profit_labyrinth.py`
- Check `min_qty` filters to reduce rejected orders
- Verify turn rotation is working (not hammering one exchange)

### Queen Neural Weights Diverging
**Symptom**: Queen confidence always 0.0 or 1.0 (saturated)  
**Cause**: Learning rate too high or too many bad outcomes  
**Fix**:
```python
# In queen_neuron.py, adjust learning rate:
self.learning_rate = 0.001  # Was 0.01 (too high)
```

### JSON Corruption (State Files)
**Symptom**: `JSONDecodeError` on startup  
**Cause**: Crash during write left partial file  
**Fix**:
```bash
# Restore from backup (atomic writes create .tmp files)
mv 7day_pending_validations.json.tmp 7day_pending_validations.json

# Or reset state (CAUTION: loses history)
echo '{}' > 7day_pending_validations.json
```

---

## When Making Changes

1. **ALWAYS USE REAL DATA** - NO SIMULATIONS, NO FAKES, NO GHOSTS, NO PHANTOMS
2. **Preserve the 3-validate-4th-execute pattern** (Batten Matrix core)
3. **Always update coherence/lambda metrics** when touching validation code
4. **Test with `--dry-run` flag** before live execution (dry-run still uses REAL market data, just doesn't execute trades)
5. **Check Queen Hive guidance** before modifying execution logic
6. **Update JSON state schemas carefully** (many modules read these)
7. **Run `python check_system_health.py`** after structural changes
8. **Use `@dataclass` for new data structures** (enables JSON serialization)
9. **Instrument new code paths with metrics** (OpenTelemetry)
10. **Feed outcomes to Queen neural learning** (`queen_neuron.py`)
11. **Document sacred number usage** (PHI, LOVE_FREQUENCY, etc.)

### CRITICAL: REAL DATA ONLY POLICY
```
⚠️ NEVER USE:
- Simulated prices
- Random/fake balances  
- Mock exchange responses
- Phantom positions
- Ghost orders

✅ ALWAYS USE:
- Live API calls to exchanges
- Real balance queries
- Actual market prices
- State files with persisted real data
- Real position data
```

When an API is rate-limited, use the **state file** (e.g., `aureon_kraken_state.json`) which contains REAL persisted data - NOT made-up values.

---

## Common Development Patterns

### Implementing a New Validation System
```python
# 1. Define dataclass for validation result
@dataclass
class NewValidationResult:
    symbol: str
    probability: float  # 0-1
    confidence: float
    reasoning: str

# 2. Create validator function
async def new_validation_pass(branch: Dict) -> float:
    """Validation pass N for Batten Matrix."""
    features = extract_features(branch)
    score = compute_validation_logic(features)
    return clip(score, 0.0, 1.0)

# 3. Integrate into probability nexus
# In aureon_probability_nexus.py:
p1 = await harmonic_validation(branch)
p2 = await coherence_validation(branch)
p3 = await new_validation_pass(branch)  # <-- Add here

# 4. Update coherence calculation
coherence = 1 - (max(p1, p2, p3) - min(p1, p2, p3))
```

### Adding a New Exchange Client
```python
# 1. Create client file: {exchange}_client.py
class NewExchangeClient:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
    
    def get_balance(self) -> Dict[str, float]:
        """Return {asset: amount}"""
        pass
    
    def get_ticker(self, symbol: str) -> Dict:
        """Return {bid, ask, last, timestamp}"""
        pass
    
    def execute_trade(self, symbol: str, side: str, quantity: float) -> Dict:
        """Execute trade, return order result"""
        pass

# 2. Add fee profile to adaptive_prime_profit_gate.py
DEFAULT_FEE_PROFILES = {
    'newexchange': {
        'maker': 0.001,  # 0.1%
        'taker': 0.0015,  # 0.15%
        'spread': 0.0005  # 0.05%
    }
}

# 3. Register in micro_profit_labyrinth.py turn rotation
exchanges = ["kraken", "binance", "alpaca", "newexchange"]
```

### Logging Best Practices
```python
import logging
logger = logging.getLogger(__name__)

# Structured logging with context
logger.info("Branch validation complete", extra={
    "branch_id": branch_id,
    "symbol": symbol,
    "coherence": coherence,
    "lambda": lambda_val,
    "pass_count": 3,
    "ready_for_4th": ready
})

# Error handling with Queen immune system
try:
    result = execute_trade(symbol, side, quantity)
except Exception as e:
    logger.error(f"Trade execution failed: {e}", exc_info=True)
    if hasattr(self, 'immune_system'):
        self.immune_system.handle_error('execution', e)
```

### Async/Await Pattern (Market Data)
```python
import asyncio
from typing import List, Dict

async def fetch_multi_exchange_data(symbols: List[str]) -> Dict:
    """Fetch data from multiple exchanges in parallel."""
    tasks = [
        fetch_kraken(symbols),
        fetch_binance(symbols),
        fetch_alpaca(symbols)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return merge_results(results)

# Usage
async def main():
    data = await fetch_multi_exchange_data(["BTC/USD", "ETH/USD"])
    # Process data...
```

---

## References
- **Harmonic Nexus Core**: Frequency-based market analysis (400–520 Hz golden zone)
- **10-9-1 Model**: Compounding strategy (10% → 9% retained → 1% reinvested)
- **Elephant Memory**: Never forgets historical patterns (`aureon_elephant_learning.py`)
- **Prime Sentinel Decree**: Gary Leckey (02.11.1991) authentication module
