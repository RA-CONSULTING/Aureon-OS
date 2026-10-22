# Aureon Quantum Trading System (AQTS)

## Part 1: System Architecture & Core QGITA Detection Engine

### System Overview
The Aureon Quantum Trading System (AQTS) combines quantum geometry insight with AI-driven decision making to automate trading across multiple cryptocurrency venues. At its heart is the Quantum Golden Insight and Timing Architecture (QGITA) engine, which seeks rare structural transitions in market behaviour by analysing golden-ratio temporal relationships and multi-metric confirmations.

### Architecture Layers

#### Layer 1 – Data Ingestion
- **Real-time price feeds:** minute-level OHLC data from supported exchanges.
- **Order book depth:** snapshots and deltas to monitor liquidity shifts.
- **Volume & volatility:** rolling measurements to capture momentum and turbulence.
- **Social sentiment:** aggregated signals from curated channels and NLP classifiers.

#### Layer 2 – QGITA Detection
- **Fibonacci time lattice generation:** derive temporal knots aligned to Fibonacci progression.
- **Curvature spike detection:** compute discrete curvature on price paths to locate sharp bends.
- **Multi-metric Lighthouse consensus:** combine coherence measures, anomaly detection, and effective gravity.
- **Confidence scoring:** scale from 0–100% based on distance beyond consensus thresholds.

#### Layer 3 – Risk Management
- **Position sizing:** cap risk exposure at 2% of portfolio equity per trade.
- **Stop-loss automation:** dynamic placement informed by curvature extremes.
- **Take-profit targets:** tiered exits keyed to signal strength and volatility regime.
- **Portfolio allocation:** allocate capital across simultaneous signals without exceeding risk limits.

#### Layer 4 – Execution
- **Multi-exchange integration:** REST/WebSocket connectivity for order placement and market data.
- **Smart order routing:** optimise fills via split orders, iceberg logic, and venue selection.
- **Trade logging:** persist orders, fills, and state transitions for auditing.
- **Performance tracking:** maintain PnL, win-rate, and efficiency metrics.

#### Layer 5 – Monitoring
- **Real-time dashboard:** visualise active positions, signals, and telemetry.
- **Alert system:** push notifications through Telegram and email.
- **Performance analytics:** historical analysis, drawdown curves, and attribution.

---

## Core QGITA Detection Engine

### Stage 1: Fibonacci-Tightened Curvature Points (FTCPs)

1. **Fibonacci Time Lattice** – generate knot timestamps using the Fibonacci sequence scaled by a base interval.
   ```python
   def generate_fibonacci_lattice(start_time, base_interval_minutes, num_points):
       fib = [0, 1]
       for i in range(2, num_points):
           fib.append(fib[i-1] + fib[i-2])
   
       knots = []
       for f in fib:
           knot_time = start_time + timedelta(minutes=base_interval_minutes * f)
           knots.append(knot_time)
   
       return knots
   ```

2. **Discrete Curvature Calculation** – estimate curvature at each knot using a second-order finite difference.
   ```python
   def calculate_curvature(prices, times):
       if len(prices) < 3 or len(times) < 3:
           return 0.0
   
       x_prev, x_curr, x_next = prices[-3], prices[-2], prices[-1]
       t_prev, t_curr, t_next = times[-3], times[-2], times[-1]
   
       dt1 = (t_curr - t_prev).total_seconds()
       dt2 = (t_next - t_curr).total_seconds()
   
       if dt1 == 0 or dt2 == 0:
           return 0.0
   
       numerator = x_next - 2 * x_curr + x_prev
       denominator = dt1 * dt2
   
       curvature = numerator / denominator
       return curvature
   ```

3. **Golden Ratio Timing Validation** – ensure the knot spacing aligns with φ⁻¹ within a tolerance.
   ```python
   PHI = 1.618033988749895
   PHI_INV = 0.618033988749895
   
   def check_golden_ratio_timing(times, tolerance=0.05):
       if len(times) < 3:
           return False
   
       t_prev, t_curr, t_next = times[-3], times[-2], times[-1]
   
       interval1 = (t_curr - t_prev).total_seconds()
       interval2 = (t_next - t_curr).total_seconds()
   
       if interval1 == 0:
           return False
   
       ratio = interval2 / interval1
       deviation = abs(ratio - PHI_INV)
       return deviation <= tolerance
   ```

4. **FTCP Detection** – declare an FTCP when golden-ratio timing and curvature spike co-occur.
   ```python
   def detect_ftcp(prices, times, curvature_threshold_percentile=90, golden_ratio_tolerance=0.05):
       kappa = calculate_curvature(prices, times)
       golden_match = check_golden_ratio_timing(times, golden_ratio_tolerance)
   
       all_curvatures = [calculate_curvature(prices[i:i+3], times[i:i+3])
                         for i in range(len(prices) - 2)]
       threshold = np.percentile(np.abs(all_curvatures), curvature_threshold_percentile)
   
       is_ftcp = golden_match and (abs(kappa) > threshold)
       return is_ftcp, kappa
   ```

5. **Effective Gravity (G_eff)** – quantify signal strength from curvature, golden-ratio adherence, and local contrast.
   ```python
   def calculate_geff(kappa, ratio, target_ratio, tolerance, prices, alpha=1.0):
       bend = abs(kappa)
       fib_match = max(0, 1 - abs(ratio - target_ratio) / tolerance)
       if len(prices) >= 2:
           local_contrast = abs(prices[-1] - prices[-2]) / 2
       else:
           local_contrast = 0
   
       geff = alpha * bend * fib_match * local_contrast
       return geff
   ```

### Stage 2: Lighthouse Consensus Validation

1. **Coherence Metrics** – evaluate trend stability and self-similarity.
   ```python
   def calculate_linear_coherence(prices, window=20):
       if len(prices) < window:
           return 0.0
   
       ema_fast = pd.Series(prices).ewm(span=12).mean().iloc[-1]
       ema_slow = pd.Series(prices).ewm(span=26).mean().iloc[-1]
       macd = ema_fast - ema_slow
   
       coherence = min(1.0, abs(macd) / (ema_slow * 0.05))
       return coherence
   
   def calculate_nonlinear_coherence(prices, window=20):
       if len(prices) < window:
           return 0.0
   
       recent = prices[-window:]
       volatility = np.std(recent) / np.mean(recent)
       coherence = 1.0 / (1.0 + volatility)
       return coherence
   
   def calculate_cross_scale_coherence(prices, scale_factor=PHI):
       if len(prices) < 20:
           return 0.0
   
       scaled_indices = [int(i * scale_factor) for i in range(len(prices))]
       scaled_indices = [i for i in scaled_indices if i < len(prices)]
   
       if len(scaled_indices) < 10:
           return 0.0
   
       original = np.array(prices[:len(scaled_indices)])
       scaled = np.array([prices[i] for i in scaled_indices])
   
       if len(original) == len(scaled):
           correlation = np.corrcoef(original, scaled)[0, 1]
           return abs(correlation)
   
       return 0.0
   ```

2. **Anomaly Pointer (Q)** – score price-volume shocks.
   ```python
   def calculate_anomaly_pointer(prices, volumes, window=10):
       if len(prices) < window or len(volumes) < window:
           return 0.0
   
       price_change = abs(prices[-1] - prices[-2]) / prices[-2]
       avg_volume = np.mean(volumes[-window:-1])
       volume_spike = volumes[-1] / avg_volume if avg_volume > 0 else 1.0
   
       q_signal = price_change * volume_spike
       return q_signal
   ```

3. **Lighthouse Intensity (L)** – geometric mean of the consensus metrics.
   ```python
   def calculate_lighthouse_intensity(c_lin, c_nonlin, c_phi, g_eff, q_signal,
                                      weights=[1, 1, 1, 1, 1]):
       metrics = [c_lin, c_nonlin, c_phi, g_eff, q_signal]
       product = 1.0
       for metric, weight in zip(metrics, weights):
           if metric > 0:
               product *= metric ** weight
           else:
               return 0.0
   
       total_weight = sum(weights)
       lighthouse = product ** (1.0 / total_weight)
       return lighthouse
   ```

4. **Lighthouse Event (LHE) Detection** – confirm events when intensity clears statistical thresholds and FTCP alignment.
   ```python
   def detect_lighthouse_event(lighthouse_history, ftcp_detected, threshold_sigma=2.0):
       if len(lighthouse_history) < 20:
           return False, 0.0
   
       current_L = lighthouse_history[-1]
       mean_L = np.mean(lighthouse_history[:-1])
       std_L = np.std(lighthouse_history[:-1])
   
       threshold = mean_L + threshold_sigma * std_L
       intensity_exceeded = current_L > threshold
   
       is_lhe = intensity_exceeded and ftcp_detected
       if is_lhe:
           confidence = min(100, ((current_L - threshold) / threshold) * 100)
       else:
           confidence = 0.0
   
       return is_lhe, confidence
   ```

### Signal Interpretation

- **BUY Signals:** positive curvature FTCP, Lighthouse confirmation, confidence above 60%, and rising cross-scale coherence.
- **SELL Signals:** negative curvature FTCP, Lighthouse confirmation, confidence above 60%, and weakening linear coherence.

### Signal Strength Tiers

| Confidence | Tier | Action |
|------------|------|--------|
| 80–100%    | 1    | Full position size |
| 60–79%     | 2    | Half position size |
| <60%       | 3    | No trade |

## API ENUM Definitions

The AQTS execution layer harmonises with Binance-style REST and WebSocket interfaces. The following enumerations keep the
frontend, orchestration services, and documentation aligned on the canonical values expected by those APIs. The values apply
uniformly across both the REST API and WebSocket API contracts.

### Symbol Status (`status`)

| Value | Meaning |
|-------|---------|
| `TRADING` | Instrument is actively tradable. |
| `END_OF_DAY` | Venue has halted matching for the day while allowing order management. |
| `HALT` | Trading halted; orders cannot be matched. |
| `BREAK` | Temporary session break (e.g. auction, circuit breaker). |

### Account & Symbol Permissions (`permissions`)

| Value | Description |
|-------|-------------|
| `SPOT` | Default spot trading permission for accounts and instruments. |

### Order Status (`status`)

| Value | Description |
|-------|-------------|
| `NEW` | The order has been accepted by the engine. |
| `PENDING_NEW` | The order is in a pending phase until the working order of an order list has been fully filled. |
| `PARTIALLY_FILLED` | A part of the order has been filled. |
| `FILLED` | The order has been completed. |
| `CANCELED` | The order has been canceled by the user. |
| `PENDING_CANCEL` | Currently unused. |
| `REJECTED` | The order was not accepted by the engine and not processed. |
| `EXPIRED` | The order was canceled according to the order type's rules (e.g. LIMIT FOK orders with no fill, LIMIT IOC or MARKET orders that partially fill) or by the exchange (e.g. orders canceled during liquidation, orders canceled during maintenance). |
| `EXPIRED_IN_MATCH` | The order was expired by the exchange due to STP (e.g. an order with EXPIRE_TAKER will match with existing orders on the book with the same account or same `tradeGroupId`). |

### Order List Status (`listStatusType`)

| Value | Description |
|-------|-------------|
| `RESPONSE` | Response to a failed list action. |
| `EXEC_STARTED` | Order list placed or updated. |
| `UPDATED` | Client order ID adjusted within the list. |
| `ALL_DONE` | Order list finished executing. |

### Order List Order Status (`listOrderStatus`)

| Value | Description |
|-------|-------------|
| `EXECUTING` | List is active or updating. |
| `ALL_DONE` | List no longer active. |
| `REJECT` | List action failed (placement or cancellation). |

### Contingency Types (`contingencyType`)

`OCO`, `OTO`

### Allocation Types (`allocationType`)

`SOR`

### Order Types (`orderTypes`, `type`)

`LIMIT`, `MARKET`, `STOP_LOSS`, `STOP_LOSS_LIMIT`, `TAKE_PROFIT`, `TAKE_PROFIT_LIMIT`, `LIMIT_MAKER`

### Order Response Types (`newOrderRespType`)

`ACK`, `RESULT`, `FULL`

### Working Floor (`workingFloor`)

`EXCHANGE`, `SOR`

### Order Side (`side`)

`BUY`, `SELL`

### Time in Force (`timeInForce`)

| Value | Description |
|-------|-------------|
| `GTC` | Good Til Canceled — an order will be on the book unless it is canceled. |
| `IOC` | Immediate Or Cancel — an order will try to fill as much as it can before the order expires. |
| `FOK` | Fill or Kill — an order will expire if the full order cannot be filled upon execution. |

### Rate Limiters (`rateLimitType`)

| Value | Example Configuration |
|-------|------------------------|
| `REQUEST_WEIGHT` | `{ "rateLimitType": "REQUEST_WEIGHT", "interval": "MINUTE", "intervalNum": 1, "limit": 6000 }` |
| `ORDERS` | `{ "rateLimitType": "ORDERS", "interval": "SECOND", "intervalNum": 1, "limit": 10 }` |
| `RAW_REQUESTS` | `{ "rateLimitType": "RAW_REQUESTS", "interval": "MINUTE", "intervalNum": 5, "limit": 61000 }` |

### Rate Limit Intervals (`interval`)

`SECOND`, `MINUTE`, `DAY`

### STP Modes (`selfTradePreventionMode`)

`NONE`, `EXPIRE_MAKER`, `EXPIRE_TAKER`, `EXPIRE_BOTH`, `DECREMENT`

---

## Roadmap
- **Part 2:** risk management algorithms, position sizing, stop-loss / take-profit automation, portfolio allocation.
- **Part 3:** exchange API integration, order execution engine, trade logging & reconciliation.
- **Part 4:** real-time dashboard, alerting, performance analytics, backtesting framework.

_Status: Core QGITA engine complete; ready for data feed integration and execution layer build-out._
