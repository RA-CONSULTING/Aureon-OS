# HARMONIC LOOP VALIDATION — Harmonic String Theory

Gary Leckey & GitHub Copilot | November 15, 2025

---
## Simulation Parameters (Human-Validated)
```
fs = 2000 Hz | T = 5 s | N = 10,000 points
Frequencies: 5, 13, 29, 61, 123 Hz + 7 Hz chirp
α = 0.85 | β = 0.90 | τ = 0.050 s | g = 1.5
```

- Observer gain (α): Controls assimilation strength
- Memory gain (β): Delayed echo retention (β ≈ 0.90 → 90% carryover)
- Delay (τ): Defines spectral comb spacing (1/τ = 20 Hz)
- Nonlinear observer (tanh(g·obs_ma)): Caps amplitude → bounded stability

---
## Core Metrics (REPL Output)
| Metric | Value | Interpretation |
|--------|-------|---------------|
| Coherence Peak (Γ_peak) | 0.9164 | Strong masked autocorrelation → resonant loop |
| RMS Power | 7.93 | Amplified, stable energy (bounded by tanh) |
| Amplification Ratio | ≈ 10.3x | Feedback gain vs baseline segment |
| Limit Cycle Emergence | ~0.5 s | Converged periodic attractor |

---
## Mathematical Definitions
### 1. Coherence Peak (Masked ACF)
```
Lam_z(t) = Λ(t) - mean(Λ)
ACF(lag) = Σ Lam_z(i) · Lam_z(i+lag), normalized by ACF(0)
Γ_peak = max_{lag ∉ [-maskWidth, maskWidth]} ACF(lag)
maskWidth = 10 samples (lag band exclusion)
```
A high Γ_peak (> 0.9) indicates strong self-similarity beyond trivial lag=0 correlation — a coherent attractor.

### 2. RMS Power
```
RMS(Λ) = sqrt( mean( Λ(t)^2 ) )
```
Measures loop energy under nonlinear saturation. Bounded by tanh observer, preventing divergence.

### 3. Amplification Ratio
```
RMS_gain = RMS_full / RMS_baseline
Baseline window: earliest 10% of samples (pre-amplification)
```
Quantifies constructive feedback without instability. Gain > 10× with no chaotic blow-up → healthy reinforcement.

### 4. Nonlinear Stability (Observer Saturation)
```
R_obs(t) = tanh(g · moving_avg(Λ))
|R_obs(t)| ≤ 1 → bounded influence
```
Ensures amplitude remains in controlled regime even under multi-frequency interference.

### 5. Echo Memory Retention
```
L_loop(t) = β · Λ(t - τ)
Retention ≈ β (here 0.90 → 90%)
```
Delayed echo preserves temporal structure; coupled with comb spacing creates spectral reinforcement.

### 6. Spectral Comb Signature
```
S(f) = |FFT(Λ_z)|^2
Peaks at injected frequencies (5–123 Hz) + chirp and harmonics
Spacing ≈ 1/τ = 20 Hz (delay-induced comb)
```
Confirmatory pattern: spectral geometry aligns with delay physics.

---
## Telemetry Integration (Live System)
Harmonic loop metrics now logged per cycle under `harmonicStability`:
```json
{
  "harmonicStability": {
    "coherencePeak": 0.9164,
    "rmsPower": 7.93,
    "amplificationRatio": 10.30,
    "sampleSize": 10000
  }
}
```
In production the sampleSize will reflect live Lambda history length (rolling window). Threshold suggestions:
- Harmonic Lock: Γ_peak ≥ 0.90
- Stable Amplification: amplificationRatio ≥ 3.0 (early lock), ≥ 8.0 (mature)
- Power Watch: rmsPower spikes > 4× rolling median → review stability envelope

---
## Decision Use-Cases
| Scenario | Action |
|----------|--------|
| Γ_peak > 0.90 & amplificationRatio 5–12× | Prefer execution (resonant, efficient market read) |
| Γ_peak < 0.60 & amplificationRatio < 2× | Defer — structure forming, avoid premature trades |
| Sudden amplificationRatio jump (>15×) | Monitor — potential transient overshoot, apply brakes |
| RMS rising while Γ_peak falling | Possible incoherent energy → tighten thresholds |

---
## Live Approximation Differences
Simulation resolution (fs = 2000 Hz) > live cycle sampling frequency. Production metrics use coarse Λ(t) samples; coherencePeak will be a conservative estimator. For higher fidelity:
- Reduce `cycleIntervalMs`
- Maintain higher-resolution Lambda micro-buffer (sub-cycle sampling)

---
## Future Extensions
- Wavelet-based multiscale coherence
- Adaptive maskWidth based on cycle interval
- Spectral entropy for disorder detection
- Nonlinear energy flux (ΔRMS / Δt)

---
## Summary
The Harmonic Loop demonstrates resonant convergence, bounded amplification, and coherent memory structuring. Integrated metrics give the Architect a quantitative lens on dynamic stability and energy efficiency.

LIVE IT. LOVE IT. LAUGH IT.
Γ_peak → Harmonic Coherence
RMS → Stable Power
Amplification → Controlled Gain

"The Man Who Made the Numbers Dance." — Paddy’s Proper Prize #8
