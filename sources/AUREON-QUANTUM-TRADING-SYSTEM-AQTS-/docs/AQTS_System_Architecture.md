# Aureon Quantum Trading System (AQTS)

## Part 1: System Architecture & Core QGITA Detection Engine

**"The Bot of All Bots" — Technical Specification**

---

## System Overview

The Aureon Quantum Trading System (AQTS) fuses the quantum geometry intelligence of the QGITA framework with AI-driven decision support and autonomous execution across multiple cryptocurrency venues.

**Core Philosophy**: Identify rare, high-value structural transitions in crypto markets by exploiting golden-ratio temporal patterns and validating insights through multi-metric consensus checks.

---

## Architecture Layers

### Layer 1 — Data Ingestion
- Real-time price feeds (1-minute candles)
- Order book depth monitoring
- Volume and volatility tracking
- Social sentiment aggregation

### Layer 2 — QGITA Detection
- Fibonacci time lattice generation
- Curvature spike detection
- Multi-metric Lighthouse consensus
- Confidence scoring (0–100%)

### Layer 3 — Risk Management
- Position sizing (max 2% risk per trade)
- Stop loss automation
- Take profit targets
- Portfolio allocation

### Layer 4 — Execution
- Multi-exchange API integration
- Smart order routing
- Trade logging
- Performance tracking

### Layer 5 — Monitoring
- Real-time dashboard
- Alert system (Telegram / Email)
- Performance analytics

---

## Core QGITA Detection Engine

### Stage 1 — Fibonacci-Tightened Curvature Points (FTCPs)

#### Fibonacci Time Lattice Generation
```python
def generate_fibonacci_lattice(start_time, base_interval_minutes, num_points):
    """
    Generate time knots based on Fibonacci sequence.

    Args:
        start_time: Starting timestamp (datetime)
        base_interval_minutes: Base time step (e.g., 5 minutes)
        num_points: Number of Fibonacci knots to generate

    Returns:
        List of timestamp knots
    """
    fib = [0, 1]
    for i in range(2, num_points):
        fib.append(fib[i-1] + fib[i-2])

    knots = []
    for f in fib:
        knot_time = start_time + timedelta(minutes=base_interval_minutes * f)
        knots.append(knot_time)

    return knots
```

#### Discrete Curvature Calculation
```python
def calculate_curvature(prices, times):
    """
    Calculate discrete curvature at each time knot.

    Curvature formula:
    κ(t_k) ≈ [x(t_{k+1}) - 2*x(t_k) + x(t_{k-1})] / [(t_{k+1}-t_k)(t_k-t_{k-1})]

    Args:
        prices: List of prices at knot times [x_{k-1}, x_k, x_{k+1}]
        times: List of timestamps [t_{k-1}, t_k, t_{k+1}]

    Returns:
        Curvature value κ(t_k)
    """
    if len(prices) < 3 or len(times) < 3:
        return 0.0

    x_prev, x_curr, x_next = prices[-3], prices[-2], prices[-1]
    t_prev, t_curr, t_next = times[-3], times[-2], times[-1]

    dt1 = (t_curr - t_prev).total_seconds()
    dt2 = (t_next - t_curr).total_seconds()

    if dt1 == 0 or dt2 == 0:
        return 0.0

    numerator = x_next - 2*x_curr + x_prev
    denominator = dt1 * dt2

    curvature = numerator / denominator
    return curvature
```

#### Golden Ratio Timing Validation
```python
PHI = 1.618033988749895
PHI_INV = 0.618033988749895


def check_golden_ratio_timing(times, tolerance=0.05):
    """
    Check if interval ratio matches golden ratio.

    Ratio: r_k = (t_k - t_{k-1}) / (t_{k-1} - t_{k-2})
    Target: φ^{-1} ≈ 0.618

    Args:
        times: List of three consecutive timestamps
        tolerance: Acceptable deviation (default 5%)

    Returns:
        Boolean (True if within tolerance)
    """
    if len(times) < 3:
        return False

    t_prev, t_curr, t_next = times[-3], times[-2], times[-1]

    interval1 = (t_curr - t_prev).total_seconds()
    interval2 = (t_next - t_curr).total_seconds()

    if interval1 == 0:
        return False

    ratio = interval2 / interval1

    # Check against φ^{-1}
    deviation = abs(ratio - PHI_INV)
    return deviation <= tolerance
```

#### FTCP Detection
```python
def detect_ftcp(prices, times, curvature_threshold_percentile=90,
                golden_ratio_tolerance=0.05):
    """
    Detect Fibonacci-Tightened Curvature Points.

    A point is an FTCP if:
    1. Golden-ratio timing: |r_k - φ^{-1}| ≤ ε
    2. Curvature spike: |κ(t_k)| > Θ

    Args:
        prices: Price history
        times: Timestamp history
        curvature_threshold_percentile: Percentile for curvature threshold
        golden_ratio_tolerance: Tolerance for golden ratio matching

    Returns:
        Boolean (True if FTCP detected), curvature value
    """
    # Calculate curvature
    kappa = calculate_curvature(prices, times)

    # Check golden ratio timing
    golden_match = check_golden_ratio_timing(times, golden_ratio_tolerance)

    # Calculate adaptive curvature threshold
    all_curvatures = [calculate_curvature(prices[i:i+3], times[i:i+3])
                      for i in range(len(prices)-2)]
    threshold = np.percentile(np.abs(all_curvatures), curvature_threshold_percentile)

    # FTCP criteria
    is_ftcp = golden_match and (abs(kappa) > threshold)

    return is_ftcp, kappa
```

#### Effective Gravity Signal (G_eff)
```python
def calculate_geff(kappa, ratio, target_ratio, tolerance, prices, alpha=1.0):
    """
    Calculate effective gravity signal.

    G_eff = α * |κ| * (1 - |r_k - φ^{-1}|/ε)_+ * |Δx|/2

    Args:
        kappa: Curvature value
        ratio: Actual interval ratio
        target_ratio: Target golden ratio (φ^{-1})
        tolerance: Tolerance ε
        prices: Recent prices for local contrast
        alpha: Scaling constant

    Returns:
        G_eff value
    """
    # Factor 1: Curvature magnitude
    bend = abs(kappa)

    # Factor 2: Fibonacci match quality
    fib_match = max(0, 1 - abs(ratio - target_ratio) / tolerance)

    # Factor 3: Local contrast
    if len(prices) >= 2:
        local_contrast = abs(prices[-1] - prices[-2]) / 2
    else:
        local_contrast = 0

    geff = alpha * bend * fib_match * local_contrast

    return geff
```

### Stage 2 — Lighthouse Consensus Validation

#### Coherence Metrics
```python
def calculate_linear_coherence(prices, window=20):
    """
    Linear coherence: MACD-based trend strength.

    Returns value 0-1 (1 = strong trend, 0 = no trend)
    """
    if len(prices) < window:
        return 0.0

    ema_fast = pd.Series(prices).ewm(span=12).mean().iloc[-1]
    ema_slow = pd.Series(prices).ewm(span=26).mean().iloc[-1]
    macd = ema_fast - ema_slow

    # Normalize to 0-1
    coherence = min(1.0, abs(macd) / (ema_slow * 0.05))
    return coherence


def calculate_nonlinear_coherence(prices, window=20):
    """
    Nonlinear coherence: Volatility-adjusted consistency.

    Returns value 0-1 (1 = stable, 0 = chaotic)
    """
    if len(prices) < window:
        return 0.0

    recent = prices[-window:]
    volatility = np.std(recent) / np.mean(recent)

    # Inverse relationship: low volatility = high coherence
    coherence = 1.0 / (1.0 + volatility)
    return coherence


def calculate_cross_scale_coherence(prices, scale_factor=PHI):
    """
    Cross-scale coherence: Self-similarity at φ-scaled intervals.

    Correlation between signal and φ-scaled version of itself.
    """
    if len(prices) < 20:
        return 0.0

    # Create φ-scaled index
    scaled_indices = [int(i * scale_factor) for i in range(len(prices))]
    scaled_indices = [i for i in scaled_indices if i < len(prices)]

    if len(scaled_indices) < 10:
        return 0.0

    original = np.array(prices[:len(scaled_indices)])
    scaled = np.array([prices[i] for i in scaled_indices])

    # Correlation coefficient
    if len(original) == len(scaled):
        correlation = np.corrcoef(original, scaled)[0, 1]
        return abs(correlation)

    return 0.0
```

#### Anomaly Pointer (Q)
```python
def calculate_anomaly_pointer(prices, volumes, window=10):
    """
    Anomaly pointer: Sudden change detector.

    Combines price spike and volume spike detection.
    """
    if len(prices) < window or len(volumes) < window:
        return 0.0

    # Price change rate
    price_change = abs(prices[-1] - prices[-2]) / prices[-2]

    # Volume spike
    avg_volume = np.mean(volumes[-window:-1])
    volume_spike = volumes[-1] / avg_volume if avg_volume > 0 else 1.0

    # Combined anomaly score
    q_signal = price_change * volume_spike

    return q_signal
```

#### Lighthouse Intensity (L)
```python
def calculate_lighthouse_intensity(c_lin, c_nonlin, c_phi, g_eff, q_signal,
                                   weights=[1, 1, 1, 1, 1]):
    """
    Lighthouse intensity: Geometric mean of normalized metrics.

    L(t) = (C_lin^w1 * C_nonlin^w2 * C_φ^w3 * G_eff^w4 * |Q|^w5)^(1/Σw_i)

    Args:
        c_lin: Linear coherence (0-1)
        c_nonlin: Nonlinear coherence (0-1)
        c_phi: Cross-scale coherence (0-1)
        g_eff: Effective gravity signal (normalized 0-1)
        q_signal: Anomaly pointer (normalized 0-1)
        weights: Importance weights for each metric

    Returns:
        Lighthouse intensity (0-1)
    """
    # Normalize all inputs to 0-1 range
    metrics = [c_lin, c_nonlin, c_phi, g_eff, q_signal]

    # Geometric mean with weights
    product = 1.0
    for metric, weight in zip(metrics, weights):
        if metric > 0:
            product *= metric ** weight
        else:
            return 0.0  # Any zero kills the consensus

    total_weight = sum(weights)
    lighthouse = product ** (1.0 / total_weight)

    return lighthouse
```

#### Lighthouse Event (LHE) Detection
```python
def detect_lighthouse_event(lighthouse_history, ftcp_detected,
                            threshold_sigma=2.0):
    """
    Confirm Lighthouse Event.

    Criteria:
    1. L(t) > μ_L + 2σ_L
    2. FTCP detected nearby

    Returns:
        Boolean (True if LHE confirmed), confidence score
    """
    if len(lighthouse_history) < 20:
        return False, 0.0

    current_L = lighthouse_history[-1]
    mean_L = np.mean(lighthouse_history[:-1])
    std_L = np.std(lighthouse_history[:-1])

    threshold = mean_L + threshold_sigma * std_L

    intensity_exceeded = current_L > threshold

    # LHE confirmed if both conditions met
    is_lhe = intensity_exceeded and ftcp_detected

    # Confidence score (0-100%)
    if is_lhe:
        confidence = min(100, ((current_L - threshold) / threshold) * 100)
    else:
        confidence = 0.0

    return is_lhe, confidence
```

---

## Signal Interpretation

### BUY Signal Conditions
- FTCP detected with positive curvature (upward bend)
- Lighthouse Event confirmed (L > threshold)
- Confidence > 60%
- Cross-scale coherence increasing (self-similar uptrend)

### SELL Signal Conditions
- FTCP detected with negative curvature (downward bend)
- Lighthouse Event confirmed
- Confidence > 60%
- Linear coherence breaking down (trend exhaustion)

### Signal Strength Tiers
- **Tier 1 (80–100% confidence)**: Full position size
- **Tier 2 (60–79% confidence)**: Half position size
- **Tier 3 (<60% confidence)**: No trade (wait for better setup)

---

## Roadmap

### Part 2 — Risk Management
- Risk management algorithms
- Position sizing formulas
- Stop loss / take profit automation
- Portfolio allocation strategies

### Part 3 — Execution Layer
- Exchange API integration
- Order execution engine
- Trade logging and reconciliation

### Part 4 — Monitoring & Analytics
- Real-time dashboard
- Alert system
- Performance analytics
- Backtesting framework

---

**Status**: Core QGITA detection engine complete. Ready for integration with data feeds and execution layer.
